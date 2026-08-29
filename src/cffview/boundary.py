"""Boundary condition data classes for Ansys Fluent case files.

Defines the boundary condition dataclasses (:class:`VelocityInlet`,
:class:`MassFlowInlet`, ...) produced by :func:`cffview.reader.read_case`,
together with :class:`BoundaryFactory` for creating them from the raw
Scheme ``Thread Variables`` and :class:`BoundaryConsts` for mapping numeric
codes to readable strings.
"""

from enum import StrEnum
from dataclasses import dataclass, field, fields


class _CodeEnum(StrEnum):
    """Enum whose members map a Fluent numeric code to a display label.

    Each member is defined as ``(code, label)``; the member's string value is
    the display label (so ``member == label`` works in ``match`` value
    patterns), while ``member.code`` carries the numeric code from the case
    file. Use :meth:`from_code` to translate a raw code to its label.
    """

    def __new__(cls, code: str, label: str):
        obj = str.__new__(cls, label)
        obj._value_ = label
        obj.code = code
        return obj

    @classmethod
    def from_code(cls, code: str) -> str | None:
        """Return the display label for a Fluent numeric code (or None if unknown)."""
        for member in cls:
            if member.code == code:
                return member.value
        return None


class BoundaryEnums:
    # region momentum
    class VELOCITY_SPEC(_CodeEnum):
        MAGNITUDE_AND_DIRECTION = ('0', 'Magnitude and Direction')
        COMPONENTS = ('1', 'Components')
        MAGNITUDE_NORMAL_TO_BOUNDARY = ('2', 'Magnitude, Normal to Boundary')

    class FRAME_OF_REFERENCE(_CodeEnum):
        ABSOLUTE = ('0', 'Absolute')
        RELATIVE_TO_ADJACENT_CELL_ZONE = ('1', 'Ralative to Adjacent Cell Zone')

    class DIRECTION_SPEC(_CodeEnum):
        DIRECTION_VECTOR = ('0', 'Direction Vector')
        NORMAL_TO_BOUNDARY = ('1', 'Normal to Boundary')
        FROM_NEIRHBORING_CELL = ('2', 'From Neighboring Cell')

    class COORDINATE_SYSTEM(_CodeEnum):
        CARTESIAN = ('0', 'Cartesian(X, Y, Z)')
        CYLINDRICAL = ('1', 'Cylindrical(Radial, Tangential, Axial)')
        LOCAL_CYLINDRICAL = ('2', 'Local Cylindrical(Radial, Tangential, Axial)')
        LOCAL_CYLINDRICAL_SWIRL = ('3', 'Local Cylindrical Swirl')

    class KE_SPEC(_CodeEnum):
        INTENSITY_AND_LENGTH_SCALE = ('1', 'Intensity and Length Scale')
        INTENSITY_AND_VISCOSITY_RATIO = ('2', 'Intensity and Viscosity Ratio')
        INTENSITY_AND_HYDRAULIC_DIAMETER = ('3', 'Intensity and Hydraulic Diameter')

    class FLOW_SPEC(_CodeEnum):
        MASS_FLOW_RATE = ('0', 'Mass Flow Rate')
        MASS_FLUX = ('1', 'Mass Flux')
        MASS_FLUX_WITH_AVERAGE_MASS_FLUX = ('2', 'Mass Flux with Average Mass Flux')

    class P_BACKFLOW_SPEC_GEN(_CodeEnum):
        TOTAL_PRESSURE = ('0', 'Total Pressure')
        STATIC_PRESSURE = ('1', 'Static Pressure')
    # endregion momentum

    # region thermal
    class THERMAL_BC(_CodeEnum):
        TEMPERATURE = ('0', 'Temperature')
        HEAT_FLUX = ('1', 'Heat Flux')
        CONVECTION = ('2', 'Convection')
        COUPLED = ('3', 'Coupled')
        RADIATION = ('4', 'Radiation')
        MIXED = ('5', 'Mixed')
        NETWORK = ('6', 'Network')
        SKIP = ('7', 'Skip')
        VIA_SYSTEM_COUPLING = ('8', 'via System Coupling')

    class MOTION_BC(_CodeEnum):
        STATIONARY_WALL = ('0', 'Stationary Wall')
        MOVING_WALL = ('1', 'Moving Wall')

    class SHEAR_BC(_CodeEnum):
        NO_SLIP = ('0', 'No Slip')
        SPECIFIED_SHEAR = ('1', 'Specified Shear')
        MARANGONI_STRESS = ('2', 'Marangoni Stress')
        SPECULARITY_COEFFICIENT = ('3', 'Specularity Coefficient')
        FINITE_SLIP = ('4', 'Finite Slip')
        PARTIAL_SLIP = ('5', 'Partial Slip')

    class ROUGH_BC(_CodeEnum):
        STANDARD = ('0', 'Standard')
        HIGH_ROUGHNESS_ICING = ('1', 'High Roughness (Icing)')
    # endregion thermal

    # region radiation
    class RADIATION_BC(_CodeEnum):
        GRAY = ('0', 'Gray')
        SPECULAR = ('1', 'Specular')
        SEMI_TRANSPARENT = ('2', '(Semi-)Transparent')
        OPAQUE = ('3', 'Opaque')

    class T_B_B_SPEC(_CodeEnum):
        BOUNDARY_TEMPERATURE = ('0', 'Boundary Temperature')
        SPECIFIED_EXTERNAL_TEMPERATURE = ('1', 'Specified External Temperature')
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
    result: dict = {'name': data['name'], 'id_': data['id_'], 'general': {}}

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

    if other := {
        key: value for key, value in data.items()
        if key not in categorized and key not in ('name', 'id_')
    }:
        result['general'] = other
    else:
        result.pop('general')

    return result


def _map_consts(data: dict[str, str]) -> None:
    """Replace numeric codes with readable strings via :class:`BoundaryConsts`."""
    for key in filter(lambda k: k.upper() in BoundaryEnums.__dict__, data.keys()):
        data[key] = BoundaryEnums[key].from_code(data[key]) or 'unknown'


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
        case BoundaryEnums.KE_SPEC.INTENSITY_AND_LENGTH_SCALE:
            data.pop('turb_viscosity_ratio', None)
            data.pop('turb_hydraulic_diam', None)
        case BoundaryEnums.KE_SPEC.INTENSITY_AND_VISCOSITY_RATIO:
            data.pop('turb_length_scale', None)
            data.pop('turb_hydraulic_diam', None)
        case BoundaryEnums.KE_SPEC.INTENSITY_AND_HYDRAULIC_DIAMETER:
            data.pop('turb_length_scale', None)
            data.pop('turb_viscosity_ratio', None)


def _filter_direction_spec(data: dict[str, str]) -> None:
    # TODO: complete this function for 'Local Cylindrical(Radial, Tangential, Axial)' and 'Local Cylindrical Swirl'
    """Filter direction_spec and corresponding coordinate_system."""
    if data['direction_spec'] != BoundaryEnums.DIRECTION_SPEC.DIRECTION_VECTOR:
        for key in ('ni', 'nj', 'nk', 'u', 'v', 'w', 'coordinate_system'):
            data.pop(key, None)
    else:
        match data['coordinate_system']:
            case BoundaryEnums.COORDINATE_SYSTEM.CARTESIAN:
                for key in ('ni', 'nj', 'nk'):
                    data.pop(key, None)
            case BoundaryEnums.COORDINATE_SYSTEM.CYLINDRICAL:
                for key in ('u', 'v', 'w'):
                    data.pop(key, None)
            case BoundaryEnums.COORDINATE_SYSTEM.LOCAL_CYLINDRICAL:
                ...
            case BoundaryEnums.COORDINATE_SYSTEM.LOCAL_CYLINDRICAL_SWIRL:
                ...


def _filter_radiation(data: dict[str, str], rad_model: str | None) -> None:
    """Map radiation codes and drop radiation fields when no radiation model is active."""
    if rad_model not in (None, 'off'):
        if data['t_b_b_spec'] == BoundaryEnums.T_B_B_SPEC.BOUNDARY_TEMPERATURE:
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
            case BoundaryEnums.VELOCITY_SPEC.MAGNITUDE_AND_DIRECTION:
                data.pop('u', None)
                data.pop('v', None)
                data.pop('w', None)
            case BoundaryEnums.VELOCITY_SPEC.COMPONENTS:
                data.pop('ni', None)
                data.pop('nj', None)
                data.pop('nk', None)
            case BoundaryEnums.VELOCITY_SPEC.MAGNITUDE_NORMAL_TO_BOUNDARY:
                for key in ['coordinate_system', 'ni', 'nj', 'nk', 'u', 'v', 'w']:
                    data.pop(key, None)

        _filter_radiation(data, rad_model)
        return _group_by_category(self, data)


@dataclass
@BoundaryFactory.register('mass-flow-inlet')
class MassFlowInlet:
    name: str
    id_: str

    frame_of_reference: str = grouped('momentum')
    flow_spec: str = grouped('momentum')
    mass_flow: str = grouped('momentum')
    mass_flux: str = grouped('momentum')
    mass_flux_ave: str = grouped('momentum')
    p: str = grouped('momentum')

    ke_spec: str = grouped('momentum')
    turb_intensity: str = grouped('momentum')
    turb_length_scale: str = grouped('momentum')
    turb_hydraulic_diam: str = grouped('momentum')
    turb_viscosity_ratio: str = grouped('momentum')

    direction_spec: str = grouped('momentum')
    coordinate_system: str = grouped('momentum')
    ni: str = grouped('momentum')
    nj: str = grouped('momentum')
    nk: str = grouped('momentum')
    u: str = grouped('momentum')
    v: str = grouped('momentum')
    w: str = grouped('momentum')

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
        _filter_direction_spec(data)

        match data['flow_spec']:
            case BoundaryEnums.FLOW_SPEC.MASS_FLOW_RATE:
                data.pop('mass_flux', None)
                data.pop('mass_flux_ave', None)
            case BoundaryEnums.FLOW_SPEC.MASS_FLUX:
                data.pop('mass_flow', None)
                data.pop('mass_flux_ave', None)
            case BoundaryEnums.FLOW_SPEC.MASS_FLUX_WITH_AVERAGE_MASS_FLUX:
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
    u: str = grouped('momentum')
    v: str = grouped('momentum')
    w: str = grouped('momentum')

    prevent_reverse_flow: str = grouped('momentum')
    ke_spec: str = grouped('momentum')
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
        _filter_direction_spec(data)
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

    frame_of_reference: str = grouped('momentum')
    p: str = grouped('momentum')
    p_profile_multiplier: str = grouped('momentum')

    direction_spec: str = grouped('momentum')
    coordinate_system: str = grouped('momentum')
    ni: str = grouped('momentum')
    nj: str = grouped('momentum')
    nk: str = grouped('momentum')
    u: str = grouped('momentum')
    v: str = grouped('momentum')
    w: str = grouped('momentum')

    p_backflow_spec_gen: str = grouped('momentum')

    prevent_reverse_flow: str = grouped('momentum')
    radial: str = grouped('momentum')
    avg_press_spec: str = grouped('momentum')
    targeted_mf_boundary: str = grouped('momentum')

    ke_spec: str = grouped('momentum')
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

        if self.prevent_reverse_flow == '#t':
            for key in (
                'frame_of_reference', 'direction_spec', 'p_backflow_spec_gen',
                'ke_spec', 'turb_intensity', 'turb_length_scale', 'turb_hydraulic_diam', 'turb_viscosity_ratio',
                't0',
            ):
                data.pop(key, None)
        else:
            _filter_turbulence(data, turb_model)
            _filter_direction_spec(data)

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
            case BoundaryEnums.FLOW_SPEC.MASS_FLOW_RATE:
                data.pop('mass_flux', None)
                data.pop('mass_flux_ave', None)
            case BoundaryEnums.FLOW_SPEC.MASS_FLUX:
                data.pop('mass_flow', None)
                data.pop('mass_flux_ave', None)
            case BoundaryEnums.FLOW_SPEC.MASS_FLUX_WITH_AVERAGE_MASS_FLUX:
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
            case BoundaryEnums.THERMAL_BC.TEMPERATURE:
                for key in ['q', 'h', 'tinf', 'ex_emiss', 'trad']:
                    data.pop(key, None)
            case BoundaryEnums.THERMAL_BC.HEAT_FLUX:
                for key in ['t', 'h', 'tinf', 'ex_emiss', 'trad']:
                    data.pop(key, None)
            case BoundaryEnums.THERMAL_BC.CONVECTION:
                for key in ['q', 't', 'ex_emiss', 'trad']:
                    data.pop(key, None)
            case BoundaryEnums.THERMAL_BC.COUPLED | BoundaryEnums.THERMAL_BC.VIA_SYSTEM_COUPLING:
                for key in ['q', 't', 'h', 'tinf', 'ex_emiss', 'trad']:
                    data.pop(key, None)
            case BoundaryEnums.THERMAL_BC.RADIATION:
                for key in ['q', 't', 'h', 'tinf']:
                    data.pop(key, None)
            case BoundaryEnums.THERMAL_BC.MIXED:
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
                case BoundaryEnums.RADIATION_BC.SEMI_TRANSPARENT:
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
