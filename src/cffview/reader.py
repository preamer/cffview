"""Per-section readers for Ansys Fluent ``.cas.h5`` case settings.

The raw Scheme text stored under ``/settings`` in a Fluent HDF5 case file is
decoded once (:func:`_read_texts`) and then handed to per-section reader
functions registered in :data:`READERS`. :func:`read_case` dispatches to the
requested readers and merges their results.
"""

import re
from dataclasses import dataclass
from functools import lru_cache, singledispatch
from typing import Any, Callable, TypeAlias, Union

import sexpdata

NestedStrList: TypeAlias = list[Union[str, 'NestedStrList']]

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

TURB_MODEL_KEYS = [
    'rp-lam?', 'rp-ke?', 'rp-kw?', 'rp-sa?', 'sg-rsm?',
    'rp-les?', 'rp-des?', 'rp-kklw', 'rp-v2f?',
]

RADIATION_MODEL_KEYS = ['sg-rosseland?', 'sg-p1?', 'sg-dtrm?', 'sg-s2s?', 'sg-disco?']


@dataclass(frozen=True)
class CaseTexts:
    """Raw Scheme strings stored in the ``/settings`` group of a .cas.h5 file."""

    general: str
    boundary: str = ''
    cortex: str = ''


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


@lru_cache(maxsize=None)
def _parse_case_config(general: str) -> dict[str, str]:
    """Parse the ``(case-config ...)`` block into a ``name -> value`` mapping."""
    case_config = re.search(r'^\(case-config.*', general, re.M).group()
    return {
        m[0]: m[1]
        for m in re.findall(r'\(([^()\s]+)\s+\.\s+([^()\s]+)\)', case_config)
    }


@lru_cache(maxsize=None)
def _get_turb_model(general: str) -> str | None:
    """Return the turbulence model name (``ke``, ``kw``, ...), or None if unknown."""
    kvs = _parse_case_config(general)
    if kvs['rp-visc?'] == '#f':
        return 'inviscid'
    for key in TURB_MODEL_KEYS:
        if kvs[key] == '#t':
            return key[3:-1]
    return None


@lru_cache(maxsize=None)
def _get_solver_time(general: str) -> str:
    """Return ``'transient'`` or ``'steady'``."""
    return 'transient' if _parse_case_config(general)['rp-unsteady?'] == '#t' else 'steady'


@lru_cache(maxsize=None)
def _get_radiation_model(general: str) -> str:
    """Return the radiation model name (``p1``, ``s2s``, ...), or ``'false'`` if none."""
    kvs = _parse_case_config(general)
    for key in RADIATION_MODEL_KEYS:
        if kvs[key] != '#f':
            return key[3:-1]
    return 'false'


@lru_cache(maxsize=None)
def _get_gravity(general: str, dimension: str) -> dict[str, str] | str:
    gravity = re.search(r'\(gravity\?\s+([^)\s]+)\)', general).group(1)
    if gravity != '#t':
        return 'false'
    axes = ['x', 'y', 'z'] if dimension == '3d' else ['x', 'y']
    return {axis: _sel_expr(general, f'gravity/{axis}') for axis in axes}


@lru_cache(maxsize=None)
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


@lru_cache(maxsize=None)
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
def _(lst: list[str]) -> str:
    """Get sel/expr pair in list like ['constant', '.', '1'], ['profile', '12'], ..."""
    if len(lst) == 3 and lst[1] == '.':
        return f'{lst[0]}/{lst[2]}'
    elif len(lst) == 2:
        return f'{lst[0]}/{lst[1]}'
    elif len(lst) > 1:
        rest = str(list(lst[1:])).strip('[]')
        return f'{lst[0]}/{rest}'
    else:
        return lst[0]


# ------------------------------------------------------------- dispatcher


READERS: dict[str, Callable[[CaseTexts], dict[str, Any]]] = {}


def register_reader(name: str):
    """Register a reader function under a flag name."""
    def decorator(func: Callable[[CaseTexts], dict[str, Any]]) -> Callable[[CaseTexts], dict[str, Any]]:
        READERS[name] = func
        return func
    return decorator


# ------------------------------------------------------------------- solver


@register_reader('solver')
def _read_solver(texts: CaseTexts) -> dict[str, Any]:
    general = texts.general
    kvs = _parse_case_config(general)
    dimension = '3d' if kvs['rp-3d?'] == '#t' else '2d'

    solver: dict[str, Any] = {
        'type': 'pbns' if kvs['rp-seg?'] == '#t' else 'dbns',
        'time': 'transient' if kvs['rp-unsteady?'] == '#t' else 'steady',
        'dimension': dimension,
        'precision': 'double' if kvs['rp-double?'] == '#t' else 'single',
        'axi': 'true' if kvs['rp-axi?'] == '#t' else 'false',
        'init': 'hybrid' if kvs['hyb-init?'] == '#t' else 'standard',
        'turb': _get_turb_model(general),
        'energy': 'true' if kvs['rf-energy?'] == '#t' else 'false',
        'radiation': _get_radiation_model(general),
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
            if property_[1] == '.':
                data[name][property_name] = property_[2]
            elif isinstance(property_value_list := property_[1], list):
                if property_value_list[1] == '.':
                    data[name][property_name] = f'{property_value_list[0]}/{property_value_list[2]}'
                elif property_value_list[1] == 'piecewise-linear':
                    value = [f'{p[0]}, {p[2]}' for p in property_value_list[2:]]
                    data[name][property_name] = {f'{property_value_list[0]}/{property_value_list[1]}': value}
                elif property_value_list[1] in ['piecewise-polynomial', 'nasa-9-piecewise-polynomial']:
                    value = [str(p).strip('[]') for p in property_value_list[2:]]
                    data[name][property_name] = {f'{property_value_list[0]}/{property_value_list[1]}': value}
                elif property_value_list[0] == 'orthotropic':
                    value = {}
                    for p in property_value_list[1:]:
                        orth_property_name = p[0]
                        if orth_property_name in ['direction-0', 'direction-1', 'direction-2']:
                            value[orth_property_name] = [int(i) for i in p[1:]]
                        elif orth_property_name in ['k0', 'k1', 'k2']:
                            value[orth_property_name] = _sel_expr(p[1])
                    data[name][property_name] = {property_value_list[0]: value}
                else:
                    value = ' '.join(str(p) for p in property_value_list[1:])
                    data[name][property_name] = f'{property_value_list[0]}/{value}'
    return {'materials': data}


# ---------------------------------------------------------------- boundary


@register_reader('bd')
def _read_boundary(texts: CaseTexts) -> dict[str, Any]:
    from .boundary import BoundaryFactory
    boundaries = stringify_nested_list(sexpdata.parse(texts.boundary, true=None))

    data: dict[str, Any] = {}
    for boundary_info in boundaries:
        id_, type_, name, _ = [_ for _ in boundary_info[1]]
        new_boundary = BoundaryFactory.create(name, id_, type_)
        b_list = data.get(type_, [])

        for property_ in filter(lambda x: len(x) > 1, boundary_info[2]):
            property_name = property_[0].replace('-', '_').replace('?', '').replace('/', '_')
            if hasattr(new_boundary, property_name):
                if property_[1] == '.':
                    setattr(new_boundary, property_name, property_[2])
                elif len(property_) == 2:
                    setattr(new_boundary, property_name, property_[1])
                elif isinstance(property_[1], list):
                    if property_name == 'source_terms':
                        source_terms_list = property_[1:]
                        value = {}
                        for source_term in filter(lambda x: len(x) > 1, source_terms_list):
                            eq = source_term[0]
                            value[eq] = {}
                            source_property = source_term[1]
                            for source_property_ in filter(lambda x: len(x) == 3, source_property):
                                property_name: str = source_property_[0]
                                if property_name == 'profile':
                                    value[eq][property_name] = f'{source_property_[1]}/{source_property_[2]}'
                                elif source_property_[1] == '.':
                                    value[eq][property_name] = source_property_[2]
                        setattr(new_boundary, 'source_terms', value)
                    else:
                        setattr(new_boundary, property_name, _sel_expr(property_[1]))

        b_list.append(
            new_boundary.to_dict(_get_turb_model(texts.general), _get_radiation_model(texts.general))
            if hasattr(new_boundary, 'to_dict')
            else new_boundary.__dict__
        )
        data[type_] = b_list
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
        data[name] = {
            property_[0]: property_[2] if len(property_) == 3 else property_[1]
            for property_ in filter(lambda x: len(x) > 1, interface[1:])
        }
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


# --------------------------------------------- discretisation & relaxation


@register_reader('disc')
def _read_disc(texts: CaseTexts) -> dict[str, Any]:
    general = texts.general
    disc_scheme = {
        ds[0]: DISCRETIZATION_SCHEME[ds[1]]
        for ds in re.findall(r'\((.*)/scheme\s+(\d+)\)', general)
    }

    data: dict[str, Any] = {'disc-scheme': {}, 'relax-factor': {}}
    for eq in ['flow', 'pressure', 'mom', 'temperature', 'k', 'omega', 'epsilon']:
        data['disc-scheme'][eq] = disc_scheme.get(eq)

    if data['disc-scheme']['flow'] == 'Coupled':
        for eq in ['pressure', 'mom']:
            data['relax-factor'][eq] = re.search(
                rf'\(pressure-coupled/{eq}/pseudo-explicit-relax\s+([\d.]+)\)',
                general
            ).group(1)
        for eq in ['temperature', 'k', 'omega', 'epsilon', 'turb-viscosity', 'density', 'body-force']:
            data['relax-factor'][eq] = re.search(
                rf'\({eq}/pseudo-relax\s+([\d.]+)\)',
                general
            ).group(1)
    else:
        relax_factor = {
            ur[0]: ur[1]
            for ur in re.findall(r'\((.*)/relax\s+([\d.]+)\)', general)
        }
        for eq in ['pressure', 'mom', 'temperature', 'k', 'omega', 'epsilon', 'turb-viscosity', 'density', 'body-force']:
            data['relax-factor'][eq] = relax_factor.get(eq, '')

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
        property_dict = {
            property_[0]: property_[2]
            for property_ in report_def[2:]
            if len(property_) == 3 and property_[1] == '.'
        }
        data[name].update(property_dict)
        if 'volume' in type_:
            data[name]['zone-list'] = [zone for zone in report_def[4][1:]]
            data[name]['zone-names'] = [zone for zone in report_def[6][1:]]
        elif 'surface' in type_:
            data[name]['surface-ids'] = [surface for surface in report_def[4][1:]]
            data[name]['surface-names'] = [surface for surface in report_def[5][1:]]
        elif 'flux' in type_:
            data[name]['zone-ids'] = [zone for zone in report_def[2][1:]]
            data[name]['zone-names'] = [zone for zone in report_def[3][1:]]

    avg_over_state = re.search(r'(\(monitor/average-over-state.*)', general, re.M).group(1)
    avg_over_state_list = stringify_nested_list(sexpdata.loads(avg_over_state, true=None)[1])
    for rd in avg_over_state_list:
        name = rd[0]
        ids = [id_.split('.')[0] for id_ in rd[1]]
        iter_range = rd[2][:2]
        data[name]['iter-range'] = ' -> '.join(iter_range)

        if data[name].get('per-zone?') == '#f' or data[name].get('per-surface?') == '#f':
            value = rd[2][2]
            data[name]['average-over-state'] = value
        else:
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
        plotset_dict = {
            property_[0]: property_[2]
            for property_ in plotset
            if property_[0] not in ['old-props', 'report-defs']
        }
        plotset_dict['report-defs'] = plotset[6][1:]
        data[plotset_dict['name']] = plotset_dict
    return {'plotsets': data}


@register_reader('monitorsets')
def _read_monitorsets(texts: CaseTexts) -> dict[str, Any]:
    general = texts.general
    monitorsets = re.search(r'(\(monitor/monitorsets.*)', general, re.M).group(1)
    monitorsets_list = stringify_nested_list(sexpdata.loads(monitorsets, true=None)[1])

    data: dict[str, Any] = {}
    for monitorset in monitorsets_list:
        monitorset_dict = {
            property_[0]: property_[2]
            for property_ in monitorset
            if property_[0] not in ['old-props', 'report-defs']
        }
        monitorset_dict['report-defs'] = monitorset[-4][1:]
        data[monitorset_dict['name']] = monitorset_dict
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
        data['iterations'] = re.search(r'\(number-of-iterations\s+(\d+)\)', general).group(1)
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
        surface_type = surface[0]
        match surface_type:
            case 'line-surface':
                virtual_id = surface[1]
                data[virtual_id_name_map[virtual_id]] = {
                    'type': surface_type,
                    'start': surface[2],
                    'end': surface[3],
                }
            case 'plane-surface':
                virtual_id = surface[1]
                data[virtual_id_name_map[virtual_id]] = {
                    'type': surface_type,
                    'point 1': surface[2],
                    'point 2': surface[3],
                    'point 3': surface[4],
                    'bounded': surface[5],
                    'method': {
                        'type': surface[6][0],
                        'direction vector': surface[6][1],
                        'reference point': surface[6][2],
                    },
                }
            case _:
                continue
    return {'surfaces': data}


# ---------------------------------------------------------- graphics items


@register_reader('contours')
def _read_contours(texts: CaseTexts) -> dict[str, Any]:
    general = texts.general
    contours = re.search(r'(\(graphics/contours.*)', general, re.M).group(1)
    contours_list = stringify_nested_list(sexpdata.loads(contours, true=None)[1])

    data: dict[str, Any] = {}
    for contour in contours_list:
        contour_dict = {
            property_[0]: property_[2]
            for property_ in contour
            if property_[0] not in [
                'locations', 'location-ids', 'options',
                'range-options', 'range-option', 'surfaces-list',
                'color-map', 'colorings', 'annotations-list',
            ]
        }
        contour_dict['surface-list'] = contour[2][1]
        contour_dict['range-options'] = {
            range_option[0]: range_option[2]
            for range_option in contour[6][1:]
        }
        contour_dict['color-map'] = {
            color_map[0]: color_map[2]
            for color_map in contour[-7][1:]
        }
        data[contour_dict['name']] = contour_dict
    return {'contours': data}


@register_reader('vectors')
def _read_vectors(texts: CaseTexts) -> dict[str, Any]:
    general = texts.general
    vectors = re.search(r'(\(graphics/vectors\s.*)', general, re.M).group(1)
    vectors_list = stringify_nested_list(sexpdata.loads(vectors, true=None)[1])

    data: dict[str, Any] = {}
    for vector in vectors_list:
        vector_dict = {
            property_[0]: property_[2]
            for property_ in vector
            if property_[0] not in [
                'locations', 'location-ids', 'options', 'scale',
                'range-options', 'range-option', 'surfaces-list',
                'color-map', 'vector-opt', 'annotations-list',
            ]
        }
        vector_dict['surface-list'] = vector[3][1]
        vector_dict['range-options'] = {
            range_option[0]: range_option[2]
            for range_option in vector[7][1:]
        }
        vector_dict['scale'] = {
            scale[0]: scale[2]
            for scale in vector[9][1:]
        }
        vector_dict['vector-opt'] = {
            vector_opt[0]: vector_opt[2]
            for vector_opt in vector[-6][1:]
        }
        vector_dict['color-map'] = {
            color_map[0]: color_map[2]
            for color_map in vector[-5][1:]
        }
        data[vector_dict['name']] = vector_dict
    return {'vectors': data}


@register_reader('xy_plot')
def _read_xy_plot(texts: CaseTexts) -> dict[str, Any]:
    general = texts.general
    xy_plots = re.search(r'(\(graphics/xy-plot.*)', general, re.M).group(1)
    xy_plots_list = stringify_nested_list(sexpdata.loads(xy_plots, true=None)[1])

    data: dict[str, Any] = {}
    for xy_plot in xy_plots_list:
        xy_plot_dict = {
            property_[0]: property_[2]
            for property_ in xy_plot
            if property_[0] not in [
                'options', 'x-axis-data', 'y-axis-data',
                'surfaces-list', 'location-ids', 'locations',
                'option', 'plot-direction', 'axes',
            ]
        }
        xy_plot_dict['surfaces-list'] = xy_plot[7][1]
        data[xy_plot_dict['name']] = xy_plot_dict
    return {'xy-plot': data}


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
