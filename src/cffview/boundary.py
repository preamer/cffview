"""Boundary condition data classes for Ansys Fluent case files.

Defines the boundary condition dataclasses (:class:`VelocityInlet`,
:class:`MassFlowInlet`, ...) produced by :func:`cffview.reader.read_case`,
together with :class:`BoundaryFactory` for creating them from the raw
Scheme ``Thread Variables`` and :class:`BoundaryConsts` for mapping numeric
codes to readable strings.
"""

from dataclasses import dataclass, field


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


# ------------------------------------------------- shared to_dict helpers

TURBULENCE_KEYS = (
    'ke_spec', 'turb_intensity', 'turb_length_scale',
    'turb_hydraulic_diam', 'turb_viscosity_ratio',
)

RADIATION_KEYS = ('radiation_bc', 'in_emiss', 't_b_b_spec', 't_b_b')


def _map_consts(data: dict[str, str], *keys: str) -> None:
    """Replace numeric codes with readable strings via :class:`BoundaryConsts`."""
    for key in keys:
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
    _map_consts(data, 'ke_spec')
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
    _map_consts(data, 'radiation_bc', 't_b_b_spec')
    if rad_model not in (None, 'false'):
        if data['t_b_b_spec'] == 'Boundary Temperature':
            data.pop('t_b_b', None)
    else:
        for key in RADIATION_KEYS:
            data.pop(key, None)


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

    def to_dict(self, turb_model: str = None, rad_model: str = None) -> dict[str, str]:
        data = self.__dict__.copy()

        _filter_sources(data)
        if rad_model in (None, 'false'):
            data.pop('radiating', None)

        return data


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

    def to_dict(self, turb_model: str = None, rad_model: str = None) -> dict[str, str]:
        data = self.__dict__.copy()

        _filter_sources(data)
        if rad_model in (None, 'false'):
            data.pop('radiating', None)

        return data


@dataclass
@BoundaryFactory.register('velocity-inlet')
class VelocityInlet:
    name: str
    id_: str

    # region momentum
    velocity_spec: str = ''
    frame_of_reference: str = ''
    vmag: str = ''

    ke_spec: str = ''
    turb_intensity: str = ''
    turb_length_scale: str = ''
    turb_hydraulic_diam: str = ''
    turb_viscosity_ratio: str = ''

    coordinate_system: str = ''
    ni: str = ''
    nj: str = ''
    nk: str = ''
    u: str = ''
    v: str = ''
    w: str = ''
    # endregion momentum

    # region thermal
    t: str = ''
    # endregion thermal

    # region radiation
    radiation_bc: str = ''
    in_emiss: str = ''
    t_b_b_spec: str = ''
    t_b_b: str = ''
    # endregion radiation

    def to_dict(self, turb_model: str = None, rad_model: str = None) -> dict[str, str]:
        data = self.__dict__.copy()

        _map_consts(data, 'velocity_spec', 'frame_of_reference', 'coordinate_system')
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
        return data


@dataclass
@BoundaryFactory.register('mass-flow-inlet')
class MassFlowInlet:
    name: str
    id_: str

    # region momentum
    mass_flow: str = ''
    frame_of_reference: str = ''

    ke_spec: str = ''
    turb_intensity: str = ''
    turb_length_scale: str = ''
    turb_hydraulic_diam: str = ''
    turb_viscosity_ratio: str = ''

    coordinate_system: str = ''
    # endregion momentum

    # region thermal
    t0: str = ''
    # endregion thermal

    # region radiation
    radiation_bc: str = ''
    in_emiss: str = ''
    t_b_b_spec: str = ''
    t_b_b: str = ''
    # endregion radiation

    def to_dict(self, turb_model: str = None, rad_model: str = None) -> dict[str, str]:
        data = self.__dict__.copy()

        _map_consts(data, 'frame_of_reference', 'coordinate_system')
        _filter_turbulence(data, turb_model)
        _filter_radiation(data, rad_model)

        return data


@dataclass
@BoundaryFactory.register('mass-flow-outlet')
class MassFlowOutlet:
    name: str
    id_: str
    mass_flow: str = ''
    t: str = ''
    turb_intensity: str = ''
    turb_hydraulic_diam: str = ''
    turb_viscosity_ratio: str = ''


@dataclass
@BoundaryFactory.register('pressure-inlet')
class PressureInlet:
    name: str
    id_: str

    # region momentum
    frame_of_reference: str = ''
    p0: str = ''
    p: str = ''

    direction_spec: str = ''
    coordinate_system: str = ''
    ni: str = ''
    nj: str = ''
    nk: str = ''

    ke_spec: str = ''
    prevent_reverse_flow: str = ''
    turb_intensity: str = ''
    turb_length_scale: str = ''
    turb_hydraulic_diam: str = ''
    turb_viscosity_ratio: str = ''
    # endregion momentum

    # region thermal
    t0: str = ''
    # endregion thermal

    # region radiation
    radiation_bc: str = ''
    in_emiss: str = ''
    t_b_b_spec: str = ''
    t_b_b: str = ''
    # endregion radiation

    def to_dict(self, turb_model: str = None, rad_model: str = None) -> dict[str, str]:
        data = self.__dict__.copy()

        _map_consts(data, 'frame_of_reference', 'direction_spec', 'coordinate_system')
        _filter_turbulence(data, turb_model)

        if data['direction_spec'] == 'Normal to Boundary':
            for key in ['ni', 'nj', 'nk', 'coordinate_system']:
                data.pop(key, None)

        _filter_radiation(data, rad_model)
        return data


@dataclass
@BoundaryFactory.register('pressure-outlet')
class PressureOutlet:
    name: str
    id_: str

    # region momentum
    p: str = ''

    ke_spec: str = ''
    prevent_reverse_flow: str = ''
    radial: str = ''
    avg_press_spec: str = ''
    turb_intensity: str = ''
    turb_length_scale: str = ''
    targeted_mf_boundary: str = ''
    turb_hydraulic_diam: str = ''
    turb_viscosity_ratio: str = ''
    # endregion momentum

    # region thermal
    t0: str = ''
    # endregion thermal

    # region radiation
    radiation_bc: str = ''
    in_emiss: str = ''
    t_b_b_spec: str = ''
    t_b_b: str = ''
    # endregion radiation

    def to_dict(self, turb_model: str = None, rad_model: str = None) -> dict[str, str]:
        data = self.__dict__.copy()

        if self.prevent_reverse_flow == '#t':
            for key in [
                't', 'ke_spec', 'turb_intensity', 'turb_length_scale',
                'targeted_mf_boundary', 'turb_hydraulic_diam', 'turb_viscosity_ratio',
            ]:
                data.pop(key, None)
        else:
            _filter_turbulence(data, turb_model)

        _filter_radiation(data, rad_model)
        return data


@dataclass
@BoundaryFactory.register('outflow')
class Outflow:
    name: str
    id_: str
    flowrate_frac: str = ''


@dataclass
@BoundaryFactory.register('wall')
class Wall:
    name: str
    id_: str

    # region momentum
    motion_bc: str = ''
    shear_bc: str = ''
    rough_bc: str = ''
    moving: str = ''
    relative: str = ''
    roughness_height: str = ''
    roughness_const: str = ''
    # endregion momentum

    # region thermal
    d: str = ''
    q_dot: str = ''
    material: str = ''

    thermal_bc: str = ''
    q: str = ''         # heat flux
    t: str = ''         # temperature
    h: str = ''         # convection
    tinf: str = ''      # convection
    ex_emiss: str = ''  # radiation
    trad: str = ''      # radiation

    planar_conduction: str = ''
    shell_conduction: str = ''
    # endregion thermal

    # region radiation
    radiation_bc: str = ''
    in_emiss: str = ''
    band_diffuse_frac: str = ''
    # endregion radiation

    def to_dict(self, turb_model: str = None, rad_model: str = None) -> dict[str, str]:
        data = self.__dict__.copy()

        _map_consts(data, 'thermal_bc', 'motion_bc', 'shear_bc', 'rough_bc', 'radiation_bc')

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

        if rad_model not in (None, 'false'):
            match data['radiation_bc']:
                case '(Semi-)Transparent':
                    data.pop('in_emiss', None)
        else:
            data.pop('radiation_bc', None)
            data.pop('in_emiss', None)
            data.pop('band_diffuse_frac', None)

        return data


@dataclass
@BoundaryFactory.register('intake-fan')
class IntakeFan:
    name: str
    id_: str


@dataclass
@BoundaryFactory.register('exhaust-fan')
class ExhaustFan:
    name: str
    id_: str


@dataclass
@BoundaryFactory.register('inlet-vent')
class InletVent:
    name: str
    id_: str


@dataclass
@BoundaryFactory.register('outlet-vent')
class OutletVent:
    name: str
    id_: str


@dataclass
@BoundaryFactory.register('pressure-far-field')
class PressureFarField:
    name: str
    id_: str


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


@dataclass
@BoundaryFactory.register('interior')
class Interior:
    name: str
    id_: str
    is_not_a_rans_les_interface: str = ''


@dataclass
@BoundaryFactory.register('interface')
class Interface:
    name: str
    id_: str


@dataclass
@BoundaryFactory.register('overset')
class Overset:
    name: str
    id_: str


@dataclass
@BoundaryFactory.register('symmetry')
class Symmetry:
    name: str
    id_: str


@dataclass
@BoundaryFactory.register('axis')
class Axis:
    name: str
    id_: str


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


@dataclass
class NotImplementedBoundary:
    name: str
    id_: str
