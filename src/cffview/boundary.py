from dataclasses import dataclass


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
    sources_terms: str = ''
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
            data.pop('sources_terms', None)

        return data


@dataclass
@BoundaryFactory.register('solid')
class Solid:
    name: str
    id_: str
    material: str = ''
    sources: str = ''
    sources_terms: str = ''
    fixed: str = ''
    solid_motion: str = ''

    def to_dict(self) -> dict[str, str]:
        data = self.__dict__.copy()

        if data['sources'] == '#f':
            data.pop('sources_terms', None)

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

    _VELOCITY_SPEC = {
        '1': 'Magnitude and Direction',
        '2': 'Magnitude, Normal to Boundary',
        '3': 'Components',
    }

    _FRAME_OF_REFERENCE = {
        '0': 'Absolute',
        '1': 'Ralative to Adjacent Cell Zone',
    }

    _KE_SPEC = {
        '1': 'Intensity and Length Scale',
        '2': 'Intensity and Viscosity Ratio',
        '3': 'Intensity and Hydraulic Diameter',
    }

    def to_dict(self) -> dict[str, str]:
        data = self.__dict__.copy()

        data['velocity_spec'] = self._VELOCITY_SPEC.get(self.velocity_spec, 'unknown')
        data['frame_of_reference'] = self._FRAME_OF_REFERENCE.get(self.frame_of_reference, 'unknown')
        data['ke_spec'] = self._KE_SPEC.get(self.ke_spec, 'unknown')

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
    ke_spec: str = ''
    prevent_reverse_flow: str = ''
    turb_intensity: str = ''
    turb_length_scale: str = ''
    turb_hydraulic_diam: str = ''
    turb_viscosity_ratio: str = ''

    _FRAME_OF_REFERENCE = {
        '0': 'Absolute',
        '1': 'Ralative to Adjacent Cell Zone',
    }

    _KE_SPEC = {
        '1': 'Intensity and Length Scale',
        '2': 'Intensity and Viscosity Ratio',
        '3': 'Intensity and Hydraulic Diameter',
    }

    def to_dict(self) -> dict[str, str]:
        data = self.__dict__.copy()

        data['frame_of_reference'] = self._FRAME_OF_REFERENCE.get(self.frame_of_reference, 'unknown')
        data['ke_spec'] = self._KE_SPEC.get(self.ke_spec, 'unknown')

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

    _KE_SPEC = {
        '1': 'Intensity and Length Scale',
        '2': 'Intensity and Viscosity Ratio',
        '3': 'Intensity and Hydraulic Diameter',
    }

    def to_dict(self) -> dict[str, str]:
        data = self.__dict__.copy()

        if self.prevent_reverse_flow == '#t':
            for key in ['t', 'ke_spec', 'turb_intensity', 'turb_length_scale', 'targeted_mf_boundary', 'turb_hydraulic_diam', 'turb_viscosity_ratio']:
                data.pop(key, None)
        else:
            data['ke_spec'] = self._KE_SPEC.get(self.ke_spec, 'unknown')
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

    _THERMAL_BC = {
        '1': 'Heat Flux',
        '2': 'Temperature',
        '3': 'Coupled',
    }

    _MOTION_BC = {}

    _SHEAR_BC = {}

    _ROUGH_BC = {}

    _THERMAL_BC_WHITELIST = {
        '1': {'q_dot'},  # Heat Flux
        '2': {'t'},  # Temperature
        '3': set(),  # Coupled
    }

    def to_dict(self) -> dict[str, str]:
        data = self.__dict__.copy()

        allowed_attrs = self._THERMAL_BC_WHITELIST.get(self.thermal_bc, set())
        all_thermal_attrs = {'t', 'q_dot', 'h', 'q'}
        attrs_to_remove = all_thermal_attrs - allowed_attrs
        for attr in attrs_to_remove:
            data.pop(attr, None)

        data['thermal_bc'] = self._THERMAL_BC.get(self.thermal_bc, 'unknown')

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
