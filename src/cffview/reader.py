"""Per-section readers for Ansys Fluent ``.cas.h5`` case settings.

The raw Scheme text stored under ``/settings`` in a Fluent HDF5 case file is
decoded once (:func:`_read_texts`) and then handed to per-section reader
functions registered in :data:`READERS`. :func:`read_case` dispatches to the
requested readers and merges their results.
"""

import re
from collections import namedtuple
from typing import Any, Callable, Literal
from functools import lru_cache, singledispatch, partial

import sexpdata

type NestedStrList = list[str | NestedStrList]
type SubReader = Callable[[CaseTexts], dict[str, Any]]
CaseTexts = namedtuple('CaseTexts', ['general', 'boundary', 'cortex'])

# from Ansys Fluent sg.h
DISCRETIZATION_SCHEME = {
    "0": "First Order Upwind",
    "1": "Second Order Upwind",
    "2": "Power Law",
    "3": "Central Difference",
    "4": "Quick",
    "5": "Modified HRIC",
    "6": "Third-Order MUSCL",
    "7": "Bounded Central Differencing",
    "8": "CICSAM",

    # the LES flux for the cpld solver
    "9": "Low Diffusion Second Order",

    # these are for face pressure interpolation
    "10": "Standard",  # default
    "11": "Linear",
    "12": "Second Order",
    "13": "Body Force Weighted",
    "14": "PRESTO!",
    "15": "Continuity Based",

    "16": "Geo-Reconstruct",
    "17": "Donor-Acceptor",

    "18": "Modified Body Force Weighted",

    "20": "SIMPLE",
    "21": "SIMPLEC",
    "22": "PISO",
    "23": "Phase Coupled SIMPLE",
    "24": "Coupled",
    "25": "Fractional Step",
    "26": "M_P_COUPLED",
    "27": "M_P_FULL_COUPLED",

    "28": "Compressive",
    "29": "BGM",
    "30": "Phase Coupled PISO",
    "31": "Low Diffusion Central",
}

TURB_MODEL_KEYS = (
    'rp-lam?', 'rp-ke?', 'rp-kw?', 'rp-sa?', 'sg-rsm?',
    'rp-les?', 'rp-des?', 'rp-kklw', 'rp-v2f?',
)
type TurbModel = Literal['lam', 'ke', 'kw', 'sa', 'rsm', 'les', 'des', 'kklw', 'v2f']

RADIATION_MODEL_KEYS = ('sg-rosseland?', 'sg-p1?', 'sg-dtrm?', 'sg-s2s?', 'sg-disco?')
type RadiationModel = Literal['rosseland', 'p1', 'dtrm', 's2s', 'disco']


# ------------------------------------------------------------ shared helpers


def stringify_nested_list(lst: list[Any]) -> NestedStrList:
    from sexpdata import Quoted
    result = []
    for item in lst:
        if isinstance(item, Quoted):
            item = item.x  # unwrap Quoted to its inner value
        result.append(stringify_nested_list(item) if isinstance(item, list) else str(item))
    return result


def _read_texts(file_path: str, *, need_boundary: bool = False, need_cortex: bool = False) -> CaseTexts:
    """Decode the Scheme strings under ``/settings`` of a .cas.h5 file."""
    import h5py

    with h5py.File(file_path) as f:
        settings: h5py.Group = f['/settings']
        general = settings['Rampant Variables'][0].decode()
        boundary = settings['Thread Variables'][0].decode() if need_boundary else ''
        cortex = settings['Cortex Variables'][0].decode() if need_cortex else ''
    return CaseTexts(general, boundary, cortex)


@lru_cache()
def _parse_case_config(general: str) -> dict[str, str]:
    """Parse the ``(case-config ...)`` block into a ``name -> value`` mapping."""
    case_config = re.search(r'^\(case-config.*', general, re.M).group()
    return {
        m[0]: m[1]
        for m in re.findall(r'\(([^()\s]+)\s+\.\s+([^()\s]+)\)', case_config)
    }


@lru_cache()
def _get_turb_model(general: str) -> TurbModel | None:
    """Return the turbulence model name (``ke``, ``kw``, ...), or None if unknown."""
    kvs = _parse_case_config(general)
    if kvs['rp-visc?'] == '#f':
        return 'inviscid'
    for key in TURB_MODEL_KEYS:
        if kvs[key] == '#t':
            return key[3:-1]
    return None


@lru_cache()
def _get_solver_time(general: str) -> Literal['steady', 'transient']:
    """Return ``'transient'`` or ``'steady'``."""
    return 'transient' if _parse_case_config(general)['rp-unsteady?'] == '#t' else 'steady'


@lru_cache()
def _get_radiation_model(general: str) -> RadiationModel | Literal['off']:
    """Return the radiation model name (``p1``, ``s2s``, ...), or ``'off'`` if none."""
    kvs = _parse_case_config(general)
    for key in RADIATION_MODEL_KEYS:
        if kvs[key] != '#f':
            return key[3:-1]
    return 'off'


@lru_cache()
def _get_multi_phase_model(general: str) -> Literal['off', 'vof', 'mixture', 'eulerian', 'wetsteam']:
    """Return ``'#f'`` or multi-phase model(vof, drift-flux(mixture), multi-fluid(eulerian))."""
    if (mphase_model := _parse_case_config(general)['sg-mphase?']) != '#f':
        mphase_model_map = {
            'vof': 'vof',
            'drift-flux': 'mixture',
            'multi-fluid': 'eulerian',
        }
        return mphase_model_map[mphase_model]
    elif _parse_case_config(general)['sg-wetsteam?'] != '#f':
        return 'wetsteam'
    else:
        return 'off'


@lru_cache()
def _get_gravity(general: str, dimension: str) -> dict[str, str] | Literal['Off']:
    gravity = re.search(r'\(gravity\?\s+([^)\s]+)\)', general).group(1)
    if gravity != '#t':
        return 'Off'
    axes = ['x', 'y', 'z'] if dimension == '3d' else ['x', 'y']
    return {axis: _sel_expr(general, f'gravity/{axis}') for axis in axes}


@lru_cache()
def _get_operating_conditions(general: str) -> dict[str, str]:
    conditions = [
        'operating-pressure',
        'pressure-reference/x', 'pressure-reference/y', 'pressure-reference/z',
        'operating-temperature',
    ]
    use_operating_density = re.search(r'\(use-operating-density\?\s+([^)\s]+)\)', general).group(1)
    if use_operating_density == '#t':
        conditions.append('operating-density')
    return {condition: _sel_expr(general, condition) for condition in conditions}


@lru_cache()
def _get_reference_values(general: str) -> dict[str, str]:
    reference_values = [
        'area', 'depth', 'density', 'enthalpy', 'length',
        'pressure', 'temperature', 'velocity', 'viscosity',
        'gamma', 'thread', 'tol', 'yplus',
    ]
    return {
        value: re.search(rf'\(reference-{value}\s+([^)\s]+)\)', general).group(1)
        for value in reference_values
    }


@lru_cache()
def _get_flow_scheme(general: str) -> Literal['Coupled', 'SIMPLE', 'SIMPLEC', 'PISO']:
    return DISCRETIZATION_SCHEME[re.search(r'\(flow/scheme\s+(\d+)\)', general).group(1)]


@lru_cache()
def _get_pesudo_time_method(general: str) -> Literal['Off', 'Global Time Step', 'Local Time Step']:
    flow_scheme = _get_flow_scheme(general)
    if flow_scheme == 'Coupled':
        key = 'pseudo-time-method/coupled-pbns/dt-method'
    else:
        key = 'pseudo-time-method/segregated-pbns/dt-method'
    method_code = re.search(rf'\({key}\s+([\d.]+)\)', general).group(1)
    return (
        'Off' if method_code == '0'
        else 'Global Time Step' if flow_scheme == 'Coupled'
        else 'Local Time Step'
    )


@singledispatch
def _sel_expr(arg, *args) -> str:
    """Unsupported first-argument type for :func:`_sel_expr`."""
    raise TypeError(f'Unsupported argument type for _sel_expr: {type(arg).__name__}')


@_sel_expr.register(str)
def _(general: str, name: str) -> str:
    """Combine the ``-sel`` and ``-expr`` values of a setting into ``sel/expr``."""
    sel = re.search(rf'\({name}-sel\s+"([^"]+)"\)', general).group(1)
    expr = re.search(rf'\({name}-expr\s+"([^"]+)"\)', general).group(1)
    return f'{sel}/{expr}'


@_sel_expr.register(list)
def _(lst: list[str], return_expr: bool = False) -> str:
    """Get sel/expr pair in list like ['constant', '.', '1'], ['profile', '12'], ..."""
    if len(lst) == 3 and lst[1] == '.':
        return lst[2] if return_expr else f'{lst[0]}/{lst[2]}'
    elif len(lst) == 2:
        return lst[1] if return_expr else f'{lst[0]}/{lst[1]}'
    elif len(lst) > 1:
        rest = str(list(lst[1:])).strip('[]')
        return rest if return_expr else f'{lst[0]}/{rest}'
    else:
        return lst[0]


# ------------------------------------------------------------- dispatcher


READERS: dict[str, SubReader] = {}


def register_reader(name: str) -> Callable[[SubReader], SubReader]:
    """Register a reader function under a flag name."""
    def decorator(func: SubReader) -> SubReader:
        READERS[name] = func
        return func
    return decorator


# ------------------------------------------------------------------- solver


@register_reader('solver')
def _read_solver(texts: CaseTexts) -> dict[str, Any]:
    general = texts.general
    kvs = _parse_case_config(general)
    dimension = '3d' if kvs['rp-3d?'] == '#t' else '2d'
    velocity_formulation = 'absolute' if re.search(
        r'\(solve-absolute-velocities\?\s+([^)\s]+)\)', general
    ).group(1) == '#t' else 'relative'

    solver: dict[str, Any] = {
        'type': 'pbns' if kvs['rp-seg?'] == '#t' else 'dbns',
        'velocity-formulation': velocity_formulation,
        'time': 'transient' if kvs['rp-unsteady?'] == '#t' else 'steady',
        'dimension': dimension,
        'precision': 'double' if kvs['rp-double?'] == '#t' else 'single',
        'axi': 'true' if kvs['rp-axi?'] == '#t' else 'false',
        'init': 'hybrid' if kvs['hyb-init?'] == '#t' else 'standard',
        'turb': _get_turb_model(general),
        'energy': 'true' if kvs['rf-energy?'] == '#t' else 'false',
        'radiation': _get_radiation_model(general),
        'multi-phase': _get_multi_phase_model(general),
        'gravity': _get_gravity(general, dimension),
    }
    if solver['turb'] is None:
        del solver['turb']

    solver['operating-conditions'] = _get_operating_conditions(general)
    solver['reference-values'] = _get_reference_values(general)
    return {'solver': solver}

# ---------------------------------------------------------------- materials


@register_reader('mat')
def _read_materials(texts: CaseTexts) -> dict[str, Any]:
    general = texts.general
    materials = re.search(r'(\(materials.*)', general, re.M).group(1)
    materials_list = stringify_nested_list(sexpdata.loads(materials))

    data: dict[str, Any] = {}
    for material in materials_list[1]:
        name = material[0]
        data[name] = {'type': material[1]}
        for property_ in material[2:]:
            property_name = property_[0]
            match property_[1:]:
                case ['.', value]:
                    data[name][property_name] = value
                case [[sel, '.', expr], *_]:
                    data[name][property_name] = f'{sel}/{expr}'
                case [['polynomial', 'piecewise-linear', *values_list], *_]:
                    data[name][property_name] = {
                        f'polynomial/piecewise-linear': [f'{v[0]}, {v[2]}' for v in values_list]
                    }
                case [['polynomial', polynomial_type, *values_list], *_] if polynomial_type in ('piecewise-polynomial', 'nasa-9-piecewise-polynomial'):
                    data[name][property_name] = {
                        f'polynomial/{polynomial_type}': [str(v).strip('[]') for v in values_list]
                    }
                case [['orthotropic', *orth_properties], *_]:
                    value = {}
                    for orth_property in orth_properties:
                        orth_property_name = orth_property[0]
                        if orth_property_name in ('direction-0', 'direction-1', 'direction-2'):
                            value[orth_property_name] = str([int(i) for i in orth_property[1:]]).strip('[]')
                        elif orth_property_name in ('k0', 'k1', 'k2'):
                            value[orth_property_name] = _sel_expr(orth_property[1])
                    data[name][property_name] = value
                case [[sel, *values_list], *_]:
                    data[name][property_name] = {sel: [str(v).strip('[]') for v in values_list]}
                case _:
                    value = ' '.join(str(p) for p in property_[1:])
                    data[name][property_name] = f'{property_[0]}/{value}'
    return {'materials': data}


# ---------------------------------------------------------------- boundary


@register_reader('bd')
def _read_boundary(texts: CaseTexts) -> dict[str, Any]:
    from .boundary import BoundaryFactory
    boundaries = stringify_nested_list(sexpdata.parse(texts.boundary, true=None))

    def format_component(comp) -> str:
        """Format one component of a multi-value boundary property.

        Handles plain values (``'2'``), single selectors (``['constant', '.', v]``,
        ``['profile', sel, expr]``) and nested selector pairs such as
        ``[['profile', sel, expr], ['constant', '.', v]]`` (prefers the profile,
        falls back to the constant).
        """
        if isinstance(comp, str):
            return comp
        if isinstance(comp, list):
            if len(comp) == 3:
                if comp[0] == 'constant' and comp[1] == '.':
                    return f'constant/{comp[2]}'
                if comp[0] == 'profile' and comp[1]:
                    return f'profile/{comp[1]}/{comp[2]}'
            if comp and all(isinstance(item, list) for item in comp):
                for item in comp:
                    formatted = format_component(item)
                    if formatted:
                        return formatted
        return str(comp)

    data: dict[str, Any] = {}
    for boundary_info in boundaries:
        id_, type_, name, _ = [_ for _ in boundary_info[1]]
        new_boundary = BoundaryFactory.create(name, id_, type_)
        b_list: list[dict[str, str | dict[str, str]]] = data.setdefault(type_, [])

        for property_list in boundary_info[2]:
            property_name = property_list[0].replace('-', '_').replace('?', '').replace('/', '_')
            if hasattr(new_boundary, property_name):
                match property_list:
                    case [_, expr] | [_, '.', expr] if isinstance(expr, str):
                        value = expr
                    case [_, *components] if all(isinstance(i, str) for i in components):
                        value = ' '.join(components)
                    case [_, [sel, '.', expr], *_]:
                        value = f'{sel}/{expr}'
                    case [_, ['profile', sel, expr], *_]:
                        value = f'profile/{sel}/{expr}'
                    case [_, *components] if any(
                        isinstance(c, list) and c and isinstance(c[0], list)
                        for c in components
                    ):
                        value = ' '.join(format_component(c) for c in components)
                    case ['source-terms', *source_terms_list]:
                        value = {}
                        for source_term in (st for st in source_terms_list if len(st) == 2):
                            eq_name, source_property_list = source_term
                            source_property = source_property_list[0]
                            if source_property[1] == '.':
                                value[eq_name] = f'{source_property[0]}/{source_property[2]}'
                            elif source_property[0] == 'profile' and source_property[1]:
                                value[eq_name] = f'profile/{source_property[1]}/{source_property[2]}'
                    case _:
                        value = ''
                setattr(new_boundary, property_name, value)

        b_list.append(
            new_boundary.to_dict(_get_turb_model(texts.general), _get_radiation_model(texts.general))
            if hasattr(new_boundary, 'to_dict')
            else new_boundary.__dict__
        )

    return {'boundary': data}


# --------------------------------------------------------------- interfaces


@register_reader('interfaces')
def _read_interfaces(texts: CaseTexts) -> dict[str, Any]:
    general = texts.general
    interfaces = re.search(r'(\(sliding-interfaces\s+.*)', general, re.M).group(1)
    interfaces_list = stringify_nested_list(sexpdata.loads(interfaces, true=None)[1])

    data: dict[str, Any] = {}
    for interface in interfaces_list:
        name = interface[0]
        data[name] = {}
        for interface_property in interface[1:]:
            match interface_property:
                case [property_name, '.', value] | [property_name, value]:
                    data[name][property_name] = value
                case _:
                    continue
    return {'interfaces': data}


# ---------------------------------------------------- custom field functions


@register_reader('cff')
def _read_custom_field_functions(texts: CaseTexts) -> dict[str, Any]:
    cortex = texts.cortex
    cffs = re.search(r'(\(cell-function-defs\s+.*)', cortex, re.M)
    if cffs is None:
        return {'custom-field-functions': {}}
    else:
        cffs = cffs.group(1)
        names = re.findall(r'\(name\s([^)]+)\)', cffs)
        displays = re.findall(r'\(display\s([^)]+)\)', cffs)
        data: dict[str, Any] = {
            name: display.strip('"')
            for name, display in zip(names, displays)
        }
        return {'custom-field-functions': data}


# ---------------------------------------------------------------- unit table


@register_reader('units')
def _read_units(texts: CaseTexts) -> dict[str, Any]:
    """Parse the unit table from Cortex Variables; empty means default SI units."""
    units = re.search(r'(\(unit-table\s+.*?\)\s*\))', texts.cortex, re.M)
    if units is None:
        return {'units': 'Default SI units'}
    entries = re.findall(
        r'\(([^()\s]+)\s+([^()\s]+)\s+([^()\s]+)\s+([^()\s]+)\)',
        units.group(1),
    )
    return {
        'units': {
            name: (unit, scale, offset)
            for name, unit, scale, offset in entries
        }
    }


# ------------------------------------------------------- named expressions


@register_reader('ne')
def _read_named_expressions(texts: CaseTexts) -> dict[str, Any]:
    general = texts.general
    nes = re.search(r'(\(named-expressions.*)', general, re.M).group(1)
    nes_list = stringify_nested_list(sexpdata.loads(nes, true=None)[1])

    data: dict[str, Any] = {}
    for ne in nes_list:
        ne_dict = {
            property_[0]: property_[2]
            for property_ in ne
        }
        data[ne_dict['name']] = ne_dict
    return {'named-expressions': data}


# --------------------------------------------- solution methods & controls


@register_reader('solution')
def _read_solution(texts: CaseTexts) -> dict[str, Any]:
    general = texts.general
    disc_scheme = {
        ds[0]: DISCRETIZATION_SCHEME[ds[1]]
        for ds in re.findall(r'\((.*)/scheme\s+(\d+)\)', general)
    }

    data: dict[str, Any] = {'solution-methods': {}, 'solution-controls': {}}
    cell_lsq = re.search(r'\(recon/cell-lsq\?\s+([^)]+)\)', general).group(1)
    node_lsq = re.search(r'\(recon/node-lsq\?\s+([^)]+)\)', general).group(1)
    data['solution-methods']['Gradient'] = (
        'Least Squares Cell-Based' if cell_lsq == '#t'
        else 'Green-Gauss Node-Based' if node_lsq == '#t'
        else 'Green-Gauss Cell-Based'
    )
    for eq in ('flow', 'pressure', 'mom', 'temperature', 'k', 'omega', 'epsilon', 'disco'):
        data['solution-methods'][eq] = disc_scheme.get(eq)

    flux_auto = re.search(r'\(pbs/flux-auto-select\?\s+([^)]+)\)', general).group(1)
    data['solution-methods']['Flux Type'] = 'Auto Select' if flux_auto == '#t' else ''
    if data['solution-methods']['Flux Type'] != 'Auto Select':
        flux_index = re.search(r'\(pbs/flux-index\s+([\d.]+)\)', general).group(1)
        data['solution-methods']['Flux Type'] = 'Rhie-Chow: distance based' if flux_index == '0' else 'Rhie-Chow: momentum based'

    data['solution-methods']['Pseudo Time Method'] = _get_pesudo_time_method(general)

    cell_lsf = re.search(r'\(recon/cell-lsf\?\s+([^)]+)\)', general).group(1)
    data['solution-methods']['Wraped-Face Gradient Correction'] = 'On' if cell_lsf == '#t' else 'Off'
    relax = re.search(r'\(recon/relax/relax\?\s+([^)]+)\)', general).group(1)
    data['solution-methods']['High Order Term Relaxation'] = 'On' if relax == '#t' else 'Off'
    if data['solution-methods']['High Order Term Relaxation'] == 'On':
        values = {}
        relax_limit_mode = re.search(r'\(recon/relax-limit-mode\s+([\d.]+)\)', general).group(1)
        values['Type'] = 'Standard' if relax_limit_mode == '0' else 'Convection Only'
        variables = re.search(r'\(recon/relax/all\?\s+([^)]+)\)', general).group(1)
        values['Variables'] = 'All Variables' if variables == '#t' else 'Flow Variables Only'
        values['Relaxation Factor'] = re.search(r'\(recon/relax/steady-urf\s+([\d.]+)\)', general).group(1)
        data['solution-methods']['High Order Term Relaxation'] = values

    flow_scheme = data['solution-methods']['flow']
    if flow_scheme == 'Coupled':
        if data['solution-methods']['Pseudo Time Method'] != 'Off':
            data['solution-methods']['Time Scale Factor'] = _sel_expr(general, 'pseudo-auto-time-step-scale-factor')
        for eq in ('pressure', 'mom'):
            data['solution-controls'][eq] = re.search(
                rf'\(pressure-coupled/{eq}/pseudo-explicit-relax\s+([\d.]+)\)',
                general
            ).group(1)
        for eq in ('density', 'body-force', 'temperature', 'k', 'omega', 'epsilon', 'turb-viscosity', 'disco'):
            data['solution-controls'][eq] = re.search(
                rf'\({eq}/pseudo-relax\s+([\d.]+)\)',
                general
            ).group(1)
    else:
        if flow_scheme == 'SIMPLEC':
            data['solution-methods']['Skewness Correction'] = re.search(
                r'\(simplec/skew-iter\s+([\d.]+)\)', general
            ).group(1)
        elif flow_scheme == 'PISO':
            data['solution-methods']['Skewness Correction'] = re.search(
                r'\(piso/skew-iter\s+([\d.]+)\)', general
            ).group(1)
            data['solution-methods']['Neighbor Correction'] = re.search(
                r'\(piso/neighbor-iter\s+([\d.]+)\)', general
            ).group(1)
            data['solution-methods']['Skewness-Neighbor Coupling'] = re.search(
                r'\(piso/coupling\?\s+([^)]+)\)', general
            ).group(1)

        pseudo_time_method = data['solution-methods']['Pseudo Time Method']
        implicit_relax_prefix, explicit_relax_prefix = (
            ('', '') if pseudo_time_method == 'Off' else ('dual-ts-implicit-', 'dual-ts-explicit-')
        )
        if courant_number := re.search(r'\(dual-ts/courant-number\s+([\d.]+)\)', general).group(1) if pseudo_time_method != 'Off' else None:
            data['solution-methods']['pseudo-time-courant-number'] = courant_number
        implicit_relax_factor = {
            ur[0]: ur[1]
            for ur in re.findall(rf'\((.*)/{implicit_relax_prefix}relax\s+([\d.]+)\)', general)
        }
        for eq in ('pressure', 'mom', 'temperature', 'k', 'omega', 'epsilon', 'turb-viscosity'):
            data['solution-controls'][eq] = implicit_relax_factor.get(eq, '')
        explicit_relax_factor = {
            ur[0]: ur[1]
            for ur in re.findall(rf'\((.*)/{explicit_relax_prefix}relax\s+([\d.]+)\)', general)
        }
        for eq in ('density', 'body-force', 'disco'):
            data['solution-controls'][eq] = explicit_relax_factor.get(eq, '')

    turb_model = _get_turb_model(general)
    if turb_model == 'lam':
        for eq in ['k', 'omega', 'epsilon', 'turb-viscosity']:
            data['solution-methods'].pop(eq, None)
            data['solution-controls'].pop(eq, None)
    elif turb_model == 'kw':
        data['solution-methods'].pop('epsilon', None)
        data['solution-controls'].pop('epsilon', None)
    elif turb_model == 'ke':
        data['solution-methods'].pop('omega', None)
        data['solution-controls'].pop('omega', None)

    radiation_model = _get_radiation_model(general)
    data['solution-methods'].pop('disco', None) if radiation_model != 'disco' else None
    data['solution-controls'].pop('disco', None) if radiation_model != 'disco' else None

    return data


# ------------------------------------------------------ report definitions


@register_reader('rd')
def _read_report_definitions(texts: CaseTexts) -> dict[str, Any]:
    general = texts.general
    rds = re.search(r'(\(monitor/report-definitions.*)', general, re.M).group(1)
    rds_list = stringify_nested_list(sexpdata.loads(rds, true=None)[1])

    data: dict[str, Any] = {}
    for rd in rds_list:
        name = rd[0][2]
        report_def = rd[1]
        type_ = report_def[1]
        data[name] = {'type': type_}
        for report_property in report_def[2:]:
            match report_property:
                case [prop_name, '.', value]:
                    data[name][prop_name] = value
                case [prop_name, *values] if prop_name not in ('old-props', 'locations'):
                    data[name][prop_name] = values
                case _:
                    continue

    avg_over_state = re.search(r'(\(monitor/average-over-state.*)', general, re.M).group(1)
    avg_over_state_list = stringify_nested_list(sexpdata.loads(avg_over_state, true=None)[1])
    for rd in avg_over_state_list:
        name = rd[0]
        data[name]['iter-range'] = rd[2][0] + ' -> ' + rd[2][1]

        if data[name].get('per-zone?') == '#f' or data[name].get('per-surface?') == '#f' or data[name].get('type') == 'single-val-expression':
            value = rd[2][2]
            data[name]['average-over-state'] = value
        else:
            ids = [id_.split('.')[0] for id_ in rd[1]]
            values = sum(rd[2][2:], [])
            right_order_ids = data[name].get('zone-list') or data[name].get('surface-ids') or data[name].get('zone-ids')
            sorted_values = [0] * len(values)
            for i, v in zip(ids, values):
                sorted_values[right_order_ids.index(i)] = v
            data[name]['average-over-state'] = sorted_values

    return {'report-definitions': data}


# ------------------------------------------------------------- plot/monitor


@register_reader('plotsets')
def _read_plotsets(texts: CaseTexts) -> dict[str, Any]:
    general = texts.general
    plotsets = re.search(r'(\(monitor/plotsets.*)', general, re.M).group(1)
    plotsets_list = stringify_nested_list(sexpdata.loads(plotsets, true=None)[1])

    data: dict[str, Any] = {}
    for plotset in plotsets_list:
        name = plotset[0][2]
        data[name] = {}
        for plotset_property in plotset[1:]:
            match plotset_property:
                case [prop_name, '.', value]:
                    data[name][prop_name] = value
                case [prop_name, *values] if prop_name not in ('old-props'):
                    data[name][prop_name] = values
                case _:
                    continue
    return {'plotsets': data}


@register_reader('monitorsets')
def _read_monitorsets(texts: CaseTexts) -> dict[str, Any]:
    general = texts.general
    monitorsets = re.search(r'(\(monitor/monitorsets.*)', general, re.M).group(1)
    monitorsets_list = stringify_nested_list(sexpdata.loads(monitorsets, true=None)[1])

    data: dict[str, Any] = {}
    for monitorset in monitorsets_list:
        name = monitorset[0][2]
        data[name] = {}
        for monitorset_property in monitorset[1:]:
            match monitorset_property:
                case [prop_name, '.', value]:
                    data[name][prop_name] = value
                case [prop_name, *values] if prop_name not in ('old-props'):
                    data[name][prop_name] = values
                case _:
                    continue
    return {'monitorsets': data}


# ---------------------------------------------------------------- residuals


@register_reader('residuals')
def _read_residuals(texts: CaseTexts) -> dict[str, Any]:
    general = texts.general
    data: dict[str, Any] = {}

    for setting in [
        r'advanced-options\?', r'normalize\?', r'compute-local\?',
        r'scale\?', 'convergence-criterion-type', 'n-display',
        'n-save', r'plot\?', r'print\?', 'n-maximize-norms',
    ]:
        value = re.search(
            rf'\(residuals/{setting}\s+(#[tf]|[\d.]+)\)',
            general,
        ).group(1)
        data[setting.removesuffix(r'\?')] = value
    cct = data['convergence-criterion-type']
    data['convergence-criterion-type'] = 'absolute' if cct == '0' else 'none'

    residuals = 'residuals/settings-transient' if _get_solver_time(general) == 'transient' else 'residuals/settings'
    res = re.search(rf'(\({residuals}\s+.*)', general, re.M).group(1)
    res = sexpdata.loads(res, true=None)[1]
    if str(res) != '#f':
        res_list = stringify_nested_list(res)
        for eq in res_list:
            data[eq[0]] = {
                'monitor': eq[1],
                'check-convergence': eq[3],
                'absolute-criteria': eq[4],
            }
    return {'residuals': data}


# -------------------------------------------------------------- iteration


@register_reader('iter')
def _read_iter(texts: CaseTexts) -> dict[str, Any]:
    general = texts.general
    data: dict[str, Any] = {}

    if _get_solver_time(general) == 'steady':
        pseudo_time_method = _get_pesudo_time_method(general)
        if pseudo_time_method != 'Off':
            data['time-step-method'] = 'Automatic' if re.search(
                r'\(pseudo-auto-time-step\?\s+(#[tf])\)', general
            ).group(1) == '#t' else 'User-Specified'
            if data['time-step-method'] == 'User-Specified':
                data['pseudo-time-step'] = _sel_expr(general, 'pseudo-time-step')
            else:
                data['time-scale-factor'] = _sel_expr(general, 'pseudo-auto-time-step-scale-factor')
                length_scale_method = re.search(r'\(pseudo/autotime-lscale-option\s+(\d+)\)', general).group(1)
                data['length-scale-method'] = (
                    'Aggressive' if length_scale_method == '0' else
                    'Conservative' if length_scale_method == '1' else
                    'User-Specified'
                )
                if data['length-scale-method'] == 'User-Specified':
                    data['length-scale'] = re.search(
                        r'\(pseudo/autotime-lscale-userspec\s+([\d.]+)\)', general
                    ).group(1)
            data['verbosity'] = re.search(r'\(pseudo-auto-time-verbosity\s+(\d+)\)', general).group(1)

        data['iterations'] = re.search(r'\(number-of-iterations\s+(\d+)\)', general).group(1)
        data['reporting-interval'] = re.search(r'\(iteration-chunk\s+(\d+)\)', general).group(1)
        data['update-interval'] = re.search(r'\(profile/update-interval\s+(\d+)\)', general).group(1)
        data['save-steady-statistics'] = re.search(r'\(save-steady-statistics\?\s+(#[tf])\)', general).group(1)
    else:
        data['physical-time-step'] = _sel_expr(general, 'physical-time-step')
        for key in ['time-steps', 'max-iters-per-step', 'time-step', 'flow-time']:
            data[key] = re.search(rf'\({key}\s+(\d+)\)', general).group(1)

    return {'iter': data}


# ---------------------------------------------------------------- surfaces


@register_reader('surfaces')
def _read_surfaces(texts: CaseTexts) -> dict[str, Any]:
    cortex = texts.cortex

    surfaces_groups = re.search(r'(\(surfaces/groups.*)', cortex, re.M).group(1)
    surfaces_groups_list = stringify_nested_list(sexpdata.loads(surfaces_groups, true=None)[1])
    name_id_map = {
        surface[0]: surface[1][0]
        for surface in surfaces_groups_list
    }  # name -> id

    surface_id_map = re.search(r'(\(cx-surface-id-map.*)', cortex, re.M).group(1)
    surface_id_map_list = stringify_nested_list(sexpdata.loads(surface_id_map, true=None)[1])
    id_virtual_id_map = {
        id_group[0]: id_group[1]
        for id_group in surface_id_map_list
    }  # id -> virtual id

    virtual_id_name_map = {
        id_virtual_id_map[id_]: name
        for name, id_ in name_id_map.items()
    }  # virtual id -> name

    surface_def_list = re.search(r'(\(cx-surface-def-list.*)', cortex, re.M).group(1)
    surface_def_list = stringify_nested_list(sexpdata.loads(surface_def_list, true=None)[1])

    data: dict[str, Any] = {}
    for surface_def in surface_def_list:
        surface = surface_def[2]
        match surface:
            case ['line-surface', virtual_id, start, end]:
                data[virtual_id_name_map[virtual_id]] = {
                    'type': 'line-surface',
                    'start': start,
                    'end': end,
                }
            case ['plane-surface', virtual_id, point1, point2, point3, bounded, [ref_plane, direction_vector, ref_point]]:
                data[virtual_id_name_map[virtual_id]] = {
                    'type': 'plane-surface',
                    'point 1': point1,
                    'point 2': point2,
                    'point 3': point3,
                    'bounded': bounded,
                    'method': {
                        'reference plane': ref_plane,
                        'direction vector': direction_vector,
                        'reference point': ref_point,
                    }
                }
            case ['iso-surface', virtual_id, from_surface_or_zone, reference, [iso_values]]:
                data[virtual_id_name_map[virtual_id]] = {
                    'type': 'iso-surface',
                    'from': [virtual_id_name_map[vid] for vid in from_surface_or_zone],
                    'reference': reference,
                    'iso-values': iso_values,
                }
            case ['iso-clip-new', virtual_id, [*clip_surfaces_vid], reference, min_value, max_value]:
                data[virtual_id_name_map[virtual_id]] = {
                    'type': 'iso-clip-new',
                    'clip surfaces': [virtual_id_name_map[vid] for vid in clip_surfaces_vid],
                    'reference': reference,
                    'min': min_value,
                    'max': max_value,
                }
            case _:
                continue

    return {'surfaces': data}


# ---------------------------------------------------------- graphics items


def _read_graphics(texts: CaseTexts, graphics_type: str) -> dict[str, Any]:
    general = texts.general
    graphics_type = 'xy-plot' if graphics_type == 'xy_plot' else graphics_type
    graphics_item = re.search(rf'(\(graphics/{graphics_type}\s.*)', general, re.M).group(1)
    item_list = stringify_nested_list(sexpdata.loads(graphics_item, true=None)[1])

    data: dict[str, Any] = {}
    for item in item_list:
        name = item[0][2]
        data[name] = {}
        for item_property in item[1:]:
            match item_property:
                case [property_name, '.', value]:
                    data[name][property_name] = value
                case ['surfaces-list', *surfaces_list]:
                    data[name]['surfaces-list'] = surfaces_list
                case ['edge-type', edge_type, '.', _]:
                    data[name]['edge-type'] = edge_type
                case ['coloring', coloring, coloring_option, '.', _]:
                    data[name]['coloring'] = {
                        'type': coloring,
                        'option': coloring_option,
                    }
                case ['graphics-objects', *graphics_objects_list]:
                    graphics_objects = [
                        {object_property[0]: object_property[2] for object_property in graphics_object}
                        for graphics_object in graphics_objects_list
                    ]
                    data[name]['graphics-objects'] = graphics_objects
                case [property_name, *values] if property_name in (
                    'options', 'range-options', 'scale', 'vector-opt',
                    'color-map', 'log-scale', 'auto-scale', 'labels'
                ):
                    data[name][property_name] = {value[0]: value[2] for value in values}
                case _:
                    continue

    return {graphics_type: data}


for g_type in ('mesh', 'contours', 'vectors', 'pathlines', 'xy_plot', 'scene'):
    register_reader(g_type)(partial(_read_graphics, graphics_type=g_type))


# ------------------------------------------------------------- dispatcher


def read_case(file_path: str, **flags: bool) -> dict[str, Any]:
    """Read settings from a Fluent ``.cas.h5`` file.

    Each keyword flag (``solver``, ``mat``, ``bd``, ...) enables reading the
    corresponding section. With no flags given, every section is read.

    Parameters
    ----------
    file_path : str
        Path to the .cas.h5 file

    Returns
    -------
    dict[str, Any]
        A dictionary containing the case settings.
    """
    if not any(flags.values()):  # no section requested -> read everything
        flags = dict.fromkeys(READERS, True)

    texts = _read_texts(
        file_path,
        need_boundary=flags.get('bd', False),
        need_cortex=flags.get('surfaces', False) or flags.get('cff', False) or flags.get('units', False),
    )

    data: dict[str, Any] = {}
    for key, reader in READERS.items():
        if flags.get(key):
            data.update(reader(texts))
    return data
