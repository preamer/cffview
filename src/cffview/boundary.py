"""Boundary condition data classes for Ansys Fluent case files.

Defines the boundary condition dataclasses (:class:`VelocityInlet`,
:class:`MassFlowInlet`, ...) produced by :func:`cffview.reader.read_case`,
together with :class:`BoundaryFactory` for creating them from the raw
Scheme ``Thread Variables`` and :class:`BoundaryConsts` for mapping numeric
codes to readable strings.
"""

from dataclasses import dataclass, field, fields


class BoundaryConsts:
    # region momentum
    VELOCITY_SPEC = {
        '0': 'Magnitude and Direction',
        '1': 'Components',
        '2': 'Magnitude, Normal to Boundary',
    }

    FRAME_OF_REFERENCE = {
        '0': 'Absolute',
        '1': 'Ralative to Adjacent Cell Zone',
    }

    COORDINATE_SYSTEM = {
        '0': 'Cartesian(X, Y, Z)',
        '1': 'Cylindrical(Radial, Tangential, Axial)',
        '2': 'Local Cylindrical(Radial, Tangential, Axial)',
        '3': 'Local Cylindrical Swirl',
    }

    KE_SPEC = {
        '1': 'Intensity and Length Scale',
        '2': 'Intensity and Viscosity Ratio',
        '3': 'Intensity and Hydraulic Diameter',
    }

    DIRECTION_SPEC = {
        '0': 'Direction Vector',
        '1': 'Normal to Boundary',
    }

    FLOW_SPEC = {
        '0': 'Mass Flow Rate',
        '1': 'Mass Flux',
        '2': 'Mass Flux with Average Mass Flux',
    }
    # endregion momentum

    # region thermal
    THERMAL_BC = {
        '0': 'Temperature',
        '1': 'Heat Flux',
        '2': 'Convection',
        '3': 'Coupled',
        '4': 'Radiation',
        '5': 'Mixed',
        '6': 'Network',
        '7': 'Skip',
        '8': 'via System Coupling',
    }

    MOTION_BC = {
        '0': 'Stationary Wall',
        '1': 'Moving Wall',
    }

    SHEAR_BC = {
        '0': 'No Slip',
        '1': 'Specified Shear',
        '2': 'Marangoni Stress',
        '3': 'Specularity Coefficient',
        '4': 'Finite Slip',
        '5': 'Partial Slip',
    }

    ROUGH_BC = {
        '0': 'Standard',
        '1': 'High Roughness (Icing)',
    }
    # endregion thermal

    # region radiation
    RADIATION_BC = {
        '0': 'Gray',
        '1': 'Specular',
        '2': '(Semi-)Transparent',
        '3': 'Opaque',
    }

    T_B_B_SPEC = {
        '0': 'Boundary Temperature',
        '1': 'Specified External Temperature',
    }
    # endregion radiation

    @classmethod
    def __class_getitem__(cls, key: str):
        return getattr(cls, key.upper(), None)


class BoundaryFactory:
    _REGISTRY = {}

    @classmethod
    def register(cls, type_name: str):
        def decorator(subclass):
            cls._REGISTRY[type_name] = subclass
            return subclass
        return decorator

    @classmethod
    def create(cls, name: str, id_: str, type_: str):
        boundary_cls = cls._REGISTRY.get(type_, NotImplementedBoundary)
        return boundary_cls(name, id_)


# ------------------------------------------------- shared to_dict helpers


TURBULENCE_KEYS = (
    'ke_spec', 'turb_intensity', 'turb_length_scale',
    'turb_hydraulic_diam', 'turb_viscosity_ratio',
)

RADIATION_KEYS = ('radiation_bc', 'in_emiss', 't_b_b_spec', 't_b_b')


def grouped(group: str, default: str = '') -> str:
    """Field factory that tags a boundary attribute with its category group."""
    return field(default=default, metadata={'group': group})


def _group_by_category(cls, data: dict[str, str]) -> dict:
    """Split a flat boundary dict into category sub-dicts (momentum / thermal / radiation / ...).

    The categories come from each dataclass field's ``metadata['group']`` tag
    (see :func:`grouped`). ``name`` and ``id_`` stay at the top level; keys not
    tagged are collected under ``other`` (omitted when empty).
    """
    result: dict = {'name': data['name'], 'id_': data['id_']}
    groups: dict[str, list[str]] = {}
    for f in fields(cls):
        group = f.metadata.get('group')
        if group:
            groups.setdefault(group, []).append(f.name)
    categorized: set[str] = set()
    for category, keys in groups.items():
        category_data = {key: data[key] for key in keys if key in data}
        if category_data:
            result[category] = category_data
        categorized.update(keys)
    other = {
        key: value for key, value in data.items()
        if key not in categorized and key not in ('name', 'id_')
    }
    if other:
        result['other'] = other
    return result


def _map_consts(data: dict[str, str]) -> None:
    """Replace numeric codes with readable strings via :class:`BoundaryConsts`."""
    for key in filter(lambda k: k.upper() in BoundaryConsts.__dict__, data.keys()):
        data[key] = BoundaryConsts[key].get(data[key], 'unknown')


def _filter_sources(data: dict[str, str]) -> None:
    """Drop ``source_terms`` when the ``sources`` switch is off."""
    if data['sources'] == '#f':
        data.pop('source_terms', None)


def _filter_turbulence(data: dict[str, str], turb_model: str | None) -> None:
    """Keep only the turbulence parameters relevant to the active turbulence model."""
    if turb_model in ('inviscid', 'lam'):
        for key in TURBULENCE_KEYS:
            data.pop(key, None)
        return
    match data['ke_spec']:
        case 'Intensity and Length Scale':
            data.pop('turb_viscosity_ratio', None)
            data.pop('turb_hydraulic_diam', None)
        case 'Intensity and Viscosity Ratio':
            data.pop('turb_length_scale', None)
            data.pop('turb_hydraulic_diam', None)
        case 'Intensity and Hydraulic Diameter':
            data.pop('turb_length_scale', None)
            data.pop('turb_viscosity_ratio', None)


def _filter_radiation(data: dict[str, str], rad_model: str | None) -> None:
    """Map radiation codes and drop radiation fields when no radiation model is active."""
    if rad_model not in (None, 'off'):
        if data['t_b_b_spec'] == 'Boundary Temperature':
            data.pop('t_b_b', None)
    else:
        for key in RADIATION_KEYS:
            data.pop(key, None)


# region Cell Zone

@dataclass
@BoundaryFactory.register('fluid')
class Fluid:
    name: str
    id_: str

    material: str = ''
    sources: str = ''
    source_terms: dict[str, dict[str, str]] = field(default_factory=dict)
    fixed: str = ''
    mrf_motion: str = ''
    mgrid_motion: str = ''
    solid_motion: str = ''
    laminar: str = ''
    porous: str = ''
    fanzone: str = ''
    radiating: str = ''

    x_origin: str = grouped('reference-frame')
    y_origin: str = grouped('reference-frame')
    z_origin: str = grouped('reference-frame')
    axis_origin_component: str = grouped('reference-frame')
    ai: str = grouped('reference-frame')
    aj: str = grouped('reference-frame')
    ak: str = grouped('reference-frame')
    axis_direction_component: str = grouped('reference-frame')

    def to_dict(self, turb_model: str, rad_model: str) -> dict[str, str]:
        data = self.__dict__.copy()

        _filter_sources(data)
        if rad_model == 'off':
            data.pop('radiating', None)

        return _group_by_category(self, data)


@dataclass
@BoundaryFactory.register('solid')
class Solid:
    name: str
    id_: str
    material: str = ''
    sources: str = ''
    source_terms: dict[str, dict[str, str]] = field(default_factory=dict)
    fixed: str = ''
    solid_motion: str = ''
    radiating: str = ''

    x_origin: str = grouped('reference-frame')
    y_origin: str = grouped('reference-frame')
    z_origin: str = grouped('reference-frame')
    axis_origin_component: str = grouped('reference-frame')
    ai: str = grouped('reference-frame')
    aj: str = grouped('reference-frame')
    ak: str = grouped('reference-frame')
    axis_direction_component: str = grouped('reference-frame')

    def to_dict(self, turb_model: str, rad_model: str) -> dict[str, str]:
        data = self.__dict__.copy()

        _filter_sources(data)
        if rad_model == 'off':
            data.pop('radiating', None)

        return _group_by_category(self, data)

# endregion Cell Zone


# region Inlet

@dataclass
@BoundaryFactory.register('velocity-inlet')
class VelocityInlet:
    name: str
    id_: str

    velocity_spec: str = grouped('momentum')
    frame_of_reference: str = grouped('momentum')
    vmag: str = grouped('momentum')

    ke_spec: str = grouped('momentum')
    turb_intensity: str = grouped('momentum')
    turb_length_scale: str = grouped('momentum')
    turb_hydraulic_diam: str = grouped('momentum')
    turb_viscosity_ratio: str = grouped('momentum')

    coordinate_system: str = grouped('momentum')
    ni: str = grouped('momentum')
    nj: str = grouped('momentum')
    nk: str = grouped('momentum')
    u: str = grouped('momentum')
    v: str = grouped('momentum')
    w: str = grouped('momentum')

    t: str = grouped('thermal')

    radiation_bc: str = grouped('radiation')
    in_emiss: str = grouped('radiation')
    t_b_b_spec: str = grouped('radiation')
    t_b_b: str = grouped('radiation')

    def to_dict(self, turb_model: str, rad_model: str) -> dict[str, str]:
        data = self.__dict__.copy()

        _map_consts(data)
        _filter_turbulence(data, turb_model)

        match data['velocity_spec']:
            case 'Magnitude and Direction':
                data.pop('u', None)
                data.pop('v', None)
                data.pop('w', None)
            case 'Components':
                data.pop('ni', None)
                data.pop('nj', None)
                data.pop('nk', None)
            case 'Magnitude, Normal to Boundary':
                for key in ['coordinate_system', 'ni', 'nj', 'nk', 'u', 'v', 'w']:
                    data.pop(key, None)

        _filter_radiation(data, rad_model)
        return _group_by_category(self, data)


@dataclass
@BoundaryFactory.register('mass-flow-inlet')
class MassFlowInlet:
    name: str
    id_: str

    flow_spec: str = grouped('momentum')
    mass_flow: str = grouped('momentum')
    mass_flux: str = grouped('momentum')
    mass_flux_ave: str = grouped('momentum')
    frame_of_reference: str = grouped('momentum')
    p: str = grouped('momentum')

    ke_spec: str = grouped('momentum')
    turb_intensity: str = grouped('momentum')
    turb_length_scale: str = grouped('momentum')
    turb_hydraulic_diam: str = grouped('momentum')
    turb_viscosity_ratio: str = grouped('momentum')

    coordinate_system: str = grouped('momentum')

    t0: str = grouped('thermal')

    radiation_bc: str = grouped('radiation')
    in_emiss: str = grouped('radiation')
    t_b_b_spec: str = grouped('radiation')
    t_b_b: str = grouped('radiation')

    def to_dict(self, turb_model: str, rad_model: str) -> dict[str, str]:
        data = self.__dict__.copy()

        _map_consts(data)
        _filter_turbulence(data, turb_model)
        _filter_radiation(data, rad_model)

        match data['flow_spec']:
            case 'Mass Flow Rate':
                data.pop('mass_flux', None)
                data.pop('mass_flux_ave', None)
            case 'Mass Flux':
                data.pop('mass_flow', None)
                data.pop('mass_flux_ave', None)
            case 'Mass Flux with Average Mass Flux':
                data.pop('mass_flow', None)

        return _group_by_category(self, data)


@dataclass
@BoundaryFactory.register('pressure-inlet')
class PressureInlet:
    name: str
    id_: str

    frame_of_reference: str = grouped('momentum')
    p0: str = grouped('momentum')
    p: str = grouped('momentum')

    direction_spec: str = grouped('momentum')
    coordinate_system: str = grouped('momentum')
    ni: str = grouped('momentum')
    nj: str = grouped('momentum')
    nk: str = grouped('momentum')

    ke_spec: str = grouped('momentum')
    prevent_reverse_flow: str = grouped('momentum')
    turb_intensity: str = grouped('momentum')
    turb_length_scale: str = grouped('momentum')
    turb_hydraulic_diam: str = grouped('momentum')
    turb_viscosity_ratio: str = grouped('momentum')

    t0: str = grouped('thermal')

    radiation_bc: str = grouped('radiation')
    in_emiss: str = grouped('radiation')
    t_b_b_spec: str = grouped('radiation')
    t_b_b: str = grouped('radiation')

    def to_dict(self, turb_model: str, rad_model: str) -> dict[str, str]:
        data = self.__dict__.copy()

        _map_consts(data)
        _filter_turbulence(data, turb_model)

        if data['direction_spec'] == 'Normal to Boundary':
            for key in ['ni', 'nj', 'nk', 'coordinate_system']:
                data.pop(key, None)

        _filter_radiation(data, rad_model)
        return _group_by_category(self, data)


@dataclass
@BoundaryFactory.register('intake-fan')
class IntakeFan:
    name: str
    id_: str


@dataclass
@BoundaryFactory.register('inlet-vent')
class InletVent:
    name: str
    id_: str


@dataclass
@BoundaryFactory.register('pressure-far-field')
class PressureFarField:
    name: str
    id_: str

# endregion Inlet


# region Outlet

@dataclass
@BoundaryFactory.register('pressure-outlet')
class PressureOutlet:
    name: str
    id_: str

    p: str = grouped('momentum')

    ke_spec: str = grouped('momentum')
    prevent_reverse_flow: str = grouped('momentum')
    radial: str = grouped('momentum')
    avg_press_spec: str = grouped('momentum')
    turb_intensity: str = grouped('momentum')
    turb_length_scale: str = grouped('momentum')
    targeted_mf_boundary: str = grouped('momentum')
    turb_hydraulic_diam: str = grouped('momentum')
    turb_viscosity_ratio: str = grouped('momentum')

    t0: str = grouped('thermal')

    radiation_bc: str = grouped('radiation')
    in_emiss: str = grouped('radiation')
    t_b_b_spec: str = grouped('radiation')
    t_b_b: str = grouped('radiation')

    def to_dict(self, turb_model: str, rad_model: str) -> dict[str, str]:
        data = self.__dict__.copy()

        _map_consts(data)

        if self.prevent_reverse_flow == '#t':
            for key in [
                't', 'ke_spec', 'turb_intensity', 'turb_length_scale',
                'targeted_mf_boundary', 'turb_hydraulic_diam', 'turb_viscosity_ratio',
            ]:
                data.pop(key, None)
        else:
            _filter_turbulence(data, turb_model)

        _filter_radiation(data, rad_model)
        return _group_by_category(self, data)


@dataclass
@BoundaryFactory.register('mass-flow-outlet')
class MassFlowOutlet:
    name: str
    id_: str

    flow_spec: str = grouped('momentum')
    mass_flow: str = grouped('momentum')
    mass_flux: str = grouped('momentum')
    mass_flux_ave: str = grouped('momentum')
    frame_of_reference: str = grouped('momentum')

    ke_spec: str = grouped('momentum')
    turb_intensity: str = grouped('momentum')
    turb_length_scale: str = grouped('momentum')
    turb_hydraulic_diam: str = grouped('momentum')
    turb_viscosity_ratio: str = grouped('momentum')

    radiation_bc: str = grouped('radiation')
    in_emiss: str = grouped('radiation')
    t_b_b_spec: str = grouped('radiation')
    t_b_b: str = grouped('radiation')

    def to_dict(self, turb_model: str, rad_model: str) -> dict[str, str]:
        data = self.__dict__.copy()

        _map_consts(data)
        _filter_turbulence(data, turb_model)
        _filter_radiation(data, rad_model)

        match data['flow_spec']:
            case 'Mass Flow Rate':
                data.pop('mass_flux', None)
                data.pop('mass_flux_ave', None)
            case 'Mass Flux':
                data.pop('mass_flow', None)
                data.pop('mass_flux_ave', None)
            case 'Mass Flux with Average Mass Flux':
                data.pop('mass_flow', None)

        return _group_by_category(self, data)


@dataclass
@BoundaryFactory.register('outflow')
class Outflow:
    name: str
    id_: str

    flowrate_frac: str = grouped('momentum')

    radiation_bc: str = grouped('radiation')
    in_emiss: str = grouped('radiation')
    t_b_b_spec: str = grouped('radiation')
    t_b_b: str = grouped('radiation')

    def to_dict(self, turb_model: str, rad_model: str) -> dict[str, str]:
        data = self.__dict__.copy()

        _map_consts(data)
        _filter_radiation(data, rad_model)

        return _group_by_category(self, data)


@dataclass
@BoundaryFactory.register('exhaust-fan')
class ExhaustFan:
    name: str
    id_: str


@dataclass
@BoundaryFactory.register('outlet-vent')
class OutletVent:
    name: str
    id_: str


# endregion Outlet


# region Wall

@dataclass
@BoundaryFactory.register('wall')
class Wall:
    name: str
    id_: str

    motion_bc: str = grouped('momentum')
    shear_bc: str = grouped('momentum')
    rough_bc: str = grouped('momentum')
    moving: str = grouped('momentum')
    relative: str = grouped('momentum')
    roughness_height: str = grouped('momentum')
    roughness_const: str = grouped('momentum')

    d: str = grouped('thermal')
    q_dot: str = grouped('thermal')
    material: str = grouped('thermal')

    thermal_bc: str = grouped('thermal')
    q: str = grouped('thermal')         # heat flux
    t: str = grouped('thermal')         # temperature
    h: str = grouped('thermal')         # convection
    tinf: str = grouped('thermal')      # convection
    ex_emiss: str = grouped('thermal')  # radiation
    trad: str = grouped('thermal')      # radiation

    planar_conduction: str = grouped('thermal')
    shell_conduction: str = grouped('thermal')

    radiation_bc: str = grouped('radiation')
    in_emiss: str = grouped('radiation')
    band_diffuse_frac: str = grouped('radiation')

    def to_dict(self, turb_model: str, rad_model: str) -> dict[str, str]:
        data = self.__dict__.copy()

        _map_consts(data)

        match data['thermal_bc']:
            case 'Temperature':
                for key in ['q', 'h', 'tinf', 'ex_emiss', 'trad']:
                    data.pop(key, None)
            case 'Heat Flux':
                for key in ['t', 'h', 'tinf', 'ex_emiss', 'trad']:
                    data.pop(key, None)
            case 'Convection':
                for key in ['q', 't', 'ex_emiss', 'trad']:
                    data.pop(key, None)
            case 'Coupled' | 'via System Coupling':
                for key in ['q', 't', 'h', 'tinf', 'ex_emiss', 'trad']:
                    data.pop(key, None)
            case 'Radiation':
                for key in ['q', 't', 'h', 'tinf']:
                    data.pop(key, None)
            case 'Mixed':
                for key in ['q', 't']:
                    data.pop(key, None)

        if data['planar_conduction'] == '#f':
            data.pop('shell_conduction', None)

        if turb_model in ['inviscid', 'lam']:
            data.pop('rough_bc', None)
            data.pop('roughness_height', None)
            data.pop('roughness_const', None)

        if rad_model not in (None, 'off'):
            match data['radiation_bc']:
                case '(Semi-)Transparent':
                    data.pop('in_emiss', None)
        else:
            data.pop('radiation_bc', None)
            data.pop('in_emiss', None)
            data.pop('band_diffuse_frac', None)

        return _group_by_category(self, data)

# endregion Wall


# region Internal

@dataclass
@BoundaryFactory.register('interior')
class Interior:
    name: str
    id_: str
    is_not_a_rans_les_interface: str = ''


@dataclass
@BoundaryFactory.register('porous-jump')
class PorousJump:
    name: str
    id_: str
    alpha: str = ''
    dm: str = ''
    c2: str = ''


@dataclass
@BoundaryFactory.register('fan')
class Fan:
    name: str
    id_: str


@dataclass
@BoundaryFactory.register('radiator')
class Radiator:
    name: str
    id_: str

# endregion Internal


# region Interface

@dataclass
@BoundaryFactory.register('interface')
class Interface:
    name: str
    id_: str

# endregion Interface


# region Overset

@dataclass
@BoundaryFactory.register('overset')
class Overset:
    name: str
    id_: str

# endregion Overset


# region Symmetry

@dataclass
@BoundaryFactory.register('symmetry')
class Symmetry:
    name: str
    id_: str

# endregion Symmetry


# region Axis

@dataclass
@BoundaryFactory.register('axis')
class Axis:
    name: str
    id_: str

# endregion Axis


# region Periodic

@dataclass
@BoundaryFactory.register('periodic')
class Periodic:
    name: str
    id_: str
    p_jump: str = ''
    x_origin: str = ''
    y_origin: str = ''
    z_origin: str = ''
    shift_x: str = ''
    shift_y: str = ''
    shift_z: str = ''

# endregion Periodic


@dataclass
class NotImplementedBoundary:
    name: str
    id_: str
