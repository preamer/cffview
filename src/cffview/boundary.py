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
        '0': 'Heat Flux',
        '1': 'Temperature',
        '2': 'Convection',
        '3': 'Coupled',
        '4': 'Radiation',
        '5': 'Mixed',
        '8': 'via System Coupling',
    }

    MOTION_BC = {
        '0': 'Stationary Wall',
        '1': 'Moving Wall',
    }

    SHEAR_BC = {
        '0': 'No Slip',
        '1': 'Specified Shear',
        '2': 'Specularity Coefficient',
        '3': 'Marangoni Stress',
    }

    ROUGH_BC = {}


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

    def to_dict(self) -> dict[str, str]:
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

    def to_dict(self) -> dict[str, str]:
        data = self.__dict__.copy()

        if data['sources'] == '#f':
            data.pop('source_terms', None)

        return data


@dataclass
@BoundaryFactory.register('velocity-inlet')
class VelocityInlet:
    name: str
    id_: str
    velocity_spec: str = ''
    frame_of_reference: str = ''
    vmag: str = ''
    t: str = ''

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

    def to_dict(self) -> dict[str, str]:
        data = self.__dict__.copy()

        data['velocity_spec'] = BoundaryConsts.VELOCITY_SPEC.get(self.velocity_spec, 'unknown')
        data['frame_of_reference'] = BoundaryConsts.FRAME_OF_REFERENCE.get(self.frame_of_reference, 'unknown')
        data['coordinate_system'] = BoundaryConsts.COORDINATE_SYSTEM.get(self.coordinate_system, 'unknown')
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
                data.pop('coordinate_system', None)
                data.pop('ni', None)
                data.pop('nj', None)
                data.pop('nk', None)
                data.pop('u', None)
                data.pop('v', None)
                data.pop('w', None)

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
    frame_of_reference: str = ''
    p0: str = ''
    p: str = ''
    t0: str = ''

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

    def to_dict(self) -> dict[str, str]:
        data = self.__dict__.copy()

        data['frame_of_reference'] = BoundaryConsts.FRAME_OF_REFERENCE.get(self.frame_of_reference, 'unknown')
        data['direction_spec'] = BoundaryConsts.DIRECTION_SPEC.get(self.direction_spec, 'unknown')
        data['coordinate_system'] = BoundaryConsts.COORDINATE_SYSTEM.get(self.coordinate_system, 'unknown')
        data['ke_spec'] = BoundaryConsts.KE_SPEC.get(self.ke_spec, 'unknown')

        if data['direction_spec'] == 'Normal to Boundary':
            data.pop('coordinate_system', None)
            data.pop('ni', None)
            data.pop('nj', None)
            data.pop('nk', None)

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
    p: str = ''
    t0: str = ''

    ke_spec: str = ''
    prevent_reverse_flow: str = ''
    radial: str = ''
    avg_press_spec: str = ''
    turb_intensity: str = ''
    turb_length_scale: str = ''
    targeted_mf_boundary: str = ''
    turb_hydraulic_diam: str = ''
    turb_viscosity_ratio: str = ''

    def to_dict(self) -> dict[str, str]:
        data = self.__dict__.copy()

        if self.prevent_reverse_flow == '#t':
            for key in [
                't', 'ke_spec', 'turb_intensity', 'turb_length_scale',
                'targeted_mf_boundary', 'turb_hydraulic_diam', 'turb_viscosity_ratio',
            ]:
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
    d: str = ''
    q_dot: str = ''
    material: str = ''

    thermal_bc: str = ''
    t: str = ''
    q: str = ''
    h: str = ''

    motion_bc: str = ''
    shear_bc: str = ''
    rough_bc: str = ''
    moving: str = ''
    relative: str = ''
    roughness_height: str = ''
    roughness_const: str = ''

    planar_conduction: str = ''
    shell_conduction: str = ''

    def to_dict(self) -> dict[str, str]:
        data = self.__dict__.copy()

        data['thermal_bc'] = BoundaryConsts.THERMAL_BC.get(self.thermal_bc, 'unknown')
        data['motion_bc'] = BoundaryConsts.MOTION_BC.get(self.motion_bc, 'unknown')
        data['shear_bc'] = BoundaryConsts.SHEAR_BC.get(self.shear_bc, 'unknown')

        match data['thermal_bc']:
            case 'Heat Flux':
                data.pop('t', None)
                data.pop('q', None)
                data.pop('h', None)
            case 'Temperature':
                data.pop('q_dot', None)
                data.pop('q', None)
                data.pop('h', None)
            case 'Coupled':
                data.pop('q_dot', None)
                data.pop('t', None)
                data.pop('q', None)
                data.pop('h', None)

        if data['planar_conduction'] == '#f':
            data.pop('shell_conduction', None)

        return data


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


@dataclass
@BoundaryFactory.register('interface')
class Interface:
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
class NotImplementedBoundary:
    name: str
    id_: str
