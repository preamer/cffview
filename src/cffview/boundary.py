from dataclasses import dataclass, field


class BoundaryConsts:
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

    def to_dict(self, turb_model: str = None) -> dict[str, str]:
        data = self.__dict__.copy()

        if data['sources'] == '#f':
            data.pop('source_terms', None)

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

    def to_dict(self, turb_model: str = None) -> dict[str, str]:
        data = self.__dict__.copy()

        if data['sources'] == '#f':
            data.pop('source_terms', None)

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

    def to_dict(self, turb_model: str = None) -> dict[str, str]:
        data = self.__dict__.copy()

        for key in ['velocity_spec', 'frame_of_reference', 'coordinate_system', 'ke_spec']:
            data[key] = BoundaryConsts[key].get(data[key], 'unknown')

        if turb_model in ['inviscid', 'lam']:
            for key in ['ke_spec', 'turb_length_scale', 'turb_hydraulic_diam', 'turb_viscosity_ratio', 'turb_intensity']:
                data.pop(key, None)
        else:
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

        return data


@dataclass
@BoundaryFactory.register('mass-flow-inlet')
class MassFlowInlet:
    name: str
    id_: str
    mass_flow: str = ''
    t: str = ''
    turb_intensity: str = ''
    turb_hydraulic_diam: str = ''
    turb_viscosity_ratio: str = ''


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

    def to_dict(self, turb_model: str = None) -> dict[str, str]:
        data = self.__dict__.copy()

        for key in ['frame_of_reference', 'direction_spec', 'coordinate_system', 'ke_spec']:
            data[key] = BoundaryConsts[key].get(data[key], 'unknown')

        if data['direction_spec'] == 'Normal to Boundary':
            for key in ['ni', 'nj', 'nk', 'coordinate_system']:
                data.pop(key, None)

        if turb_model in ['inviscid', 'lam']:
            for key in ['ke_spec', 'turb_length_scale', 'turb_hydraulic_diam', 'turb_viscosity_ratio', 'turb_intensity']:
                data.pop(key, None)
        else:
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

    def to_dict(self, turb_model: str = None) -> dict[str, str]:
        data = self.__dict__.copy()

        if self.prevent_reverse_flow == '#t':
            for key in [
                't', 'ke_spec', 'turb_intensity', 'turb_length_scale',
                'targeted_mf_boundary', 'turb_hydraulic_diam', 'turb_viscosity_ratio',
            ]:
                data.pop(key, None)
        else:
            if turb_model in ['inviscid', 'lam']:
                for key in ['ke_spec', 'turb_length_scale', 'turb_hydraulic_diam', 'turb_viscosity_ratio', 'turb_intensity']:
                    data.pop(key, None)
            else:
                data['ke_spec'] = BoundaryConsts.KE_SPEC.get(self.ke_spec, 'unknown')
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

    def to_dict(self, turb_model: str = None) -> dict[str, str]:
        data = self.__dict__.copy()

        for key in ['thermal_bc', 'motion_bc', 'shear_bc', 'rough_bc']:
            data[key] = BoundaryConsts[key].get(data[key], 'unknown')

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
    is_not_a_res_lans_interface: str = ''


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
