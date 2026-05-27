from dataclasses import dataclass


@dataclass
class Fluid:
    name: str
    id_: str
    material: str = ""
    sources: str = ""


@dataclass
class Solid:
    name: str
    id_: str
    material: str = ""
    sources: str = ""


@dataclass
class VelocityInlet:
    name: str
    id_: str
    vmag: str = ""
    t: str = ""
    turb_intensity: str = ""
    turb_hydraulic_diam: str = ""
    turb_viscosity_ratio: str = ""


@dataclass
class MassFlowInlet:
    name: str
    id_: str
    mass_flow: str = ""
    t: str = ""
    turb_intensity: str = ""
    turb_hydraulic_diam: str = ""
    turb_viscosity_ratio: str = ""


@dataclass
class MassFlowOutlet:
    name: str
    id_: str
    mass_flow: str = ""
    t: str = ""
    turb_intensity: str = ""
    turb_hydraulic_diam: str = ""
    turb_viscosity_ratio: str = ""


@dataclass
class PressureOutlet:
    name: str
    id_: str
    p: str = ""
    t: str = ""
    turb_intensity: str = ""
    turb_hydraulic_diam: str = ""
    turb_viscosity_ratio: str = ""


@dataclass
class Wall:
    name: str
    id_: str
    material: str = ""
    t: str = ""
    q: str = ""
    h: str = ""


@dataclass
class Interior:
    name: str
    id_: str


@dataclass
class PorousJump:
    name: str
    id_: str
    alpha: str = ""
    dm: str = ""
    c2: str = ""


@dataclass
class NotImplementedBoundary:
    name: str
    id_: str


class BoundaryFactory:
    @staticmethod
    def create(name: str, id_: str, type_: str):
        match type_:
            case "fluid":
                return Fluid(name, id_)
            case "solid":
                return Solid(name, id_)
            case "velocity-inlet":
                return VelocityInlet(name, id_)
            case "mass-flow-inlet":
                return MassFlowInlet(name, id_)
            case "mass-flow-outlet":
                return MassFlowOutlet(name, id_)
            case "pressure-outlet":
                return PressureOutlet(name, id_)
            case "wall":
                return Wall(name, id_)
            case "interior":
                return Interior(name, id_)
            case "porous-jump":
                return PorousJump(name, id_)
            case _:
                return NotImplementedBoundary(name, id_)
