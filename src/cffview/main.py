from typing import Literal, TypeAlias, Union


def print_version(file_path: str) -> None:
    """Get the version of the .h5 file

    Parameters
    ---------
    file_path : str
        Path to the .h5 file

    Returns
    -------
    str
        Version of the .h5 file
    """
    import h5py

    with h5py.File(file_path) as f:
        print(f['/settings/Version'][0].decode())


def read_case(file_path: str, **kwargs) -> dict[
    Literal[
        'solver', 'materials', 'boundary', 'interfaces', 'named-expressions',
        'disc-scheme', 'report-definitions', 'plotsets', 'monitorsets',
        'residuals', 'iter', 'surfaces', 'contours', 'vectors', 'xy-plot',
    ],
    dict[str]
]:
    """Read the cas.h5 file

    Parameters
    ---------
    file_path : str
        Path to the cas.h5 file

    Returns
    -------
    dict[Literal[...], dict[str]]
        A dictionary containing the case settings
    """
    import re
    import h5py
    import sexpdata
    from .utils import stringify_nested_list

    NestedStrList: TypeAlias = list[Union[str, 'NestedStrList']]

    if not any(kwargs.values()):  # all False, means `cffview case.cas.h5`, no extra params
        kwargs = dict.fromkeys(kwargs.keys(), True)

    with h5py.File(file_path) as f:
        settings: h5py.Group = f['/settings']
        general_info = settings['Rampant Variables'][0].decode()
        if kwargs['bd']:
            boundary_info = settings['Thread Variables'][0].decode()
        if kwargs['surfaces']:
            cortex_info = settings['Cortex Variables'][0].decode()

    data = {}

    if kwargs['solver']:
        case_config = re.search(
            r'^\(case-config.*',
            general_info,
            re.M
        ).group()
        kvs = {
            m[0]: m[1]
            for m in re.findall(
                r"\(([^()\s]+)\s+\.\s+([^()\s]+)\)",
                case_config
            )
        }

        data['solver'] = {}
        data['solver']['type'] = "pbns" if kvs['rp-seg?'] == "#t" else "dbns"
        data['solver']['time'] = "transient" if kvs['rp-unsteady?'] == "#t" else "steady"
        data['solver']['dimension'] = "3d" if kvs['rp-3d?'] == "#t" else "2d"
        data['solver']['precision'] = "double" if kvs['rp-double?'] == "#t" else "single"
        data['solver']['axi'] = "true" if kvs['rp-axi?'] == "#t" else "false"
        data['solver']['init'] = "hybrid" if kvs['hyb-init?'] == "#t" else "standard"

        if kvs['rp-visc?'] == "#f":
            data['solver']['turb'] = "inviscid"
        else:
            for key in [
                'rp-lam?', 'rp-ke?', 'rp-kw?', 'rp-sa?', 'sg-rsm?',
                'rp-les?', 'rp-des?', 'rp-kklw', 'rp-v2f?'
            ]:
                if kvs[key] == "#t":
                    data['solver']['turb'] = key[3:-1]
                    break

        data['solver']['energy'] = "true" if kvs['rf-energy?'] == "#t" else "false"
        data['solver']['radiation'] = "false"
        for key in ['sg-rosseland?', 'sg-p1?', 'sg-dtrm?', 'sg-s2s?', 'sg-disco?']:
            if kvs[key] != "#f":
                data['solver']['radiation'] = key[3:-1]
                break

        data['solver']['gravity'] = {}
        gravity = re.search(
            r'\(gravity\?\s+([^)\s]+)\)',
            general_info
        ).group(1)
        if gravity == "#t":
            axes = ['x', 'y', 'z'] if data['solver']['dimension'] == "3d" else ['x', 'y']
            for axis in axes:
                sel = re.search(
                    fr'\(gravity/{axis}-sel\s+"([^"]+)"\)',
                    general_info
                ).group(1)
                expr = re.search(
                    fr'\(gravity/{axis}-expr\s+"([^"]+)"\)',
                    general_info
                ).group(1)
                data['solver']['gravity'][axis] = f'{sel}/{expr}'
        else:
            data['solver']['gravity'] = "false"

        operating_conditions = [
            'operating-pressure',
            'pressure-reference/x', 'pressure-reference/y', 'pressure-reference/z',
            'operating-temperature',
        ]
        use_operating_density = re.search(
            r'\(use-operating-density\?\s+([^)\s]+)\)',
            general_info
        ).group(1)
        if use_operating_density == '#t':
            operating_conditions.append('operating-density')
        data['solver']['operating-conditions'] = {}
        for condition in operating_conditions:
            sel = re.search(
                fr'\({condition}-sel\s+"([^"]+)"\)',
                general_info
            ).group(1)
            expr = re.search(
                fr'\({condition}-expr\s+"([^"]+)"\)',
                general_info
            ).group(1)
            data['solver']['operating-conditions'][condition] = f'{sel}/{expr}'

        reference_values = [
            'area', 'depth', 'density', 'enthalpy', 'length',
            'pressure', 'temperature', 'velocity', 'viscosity',
            'gamma', 'thread', 'tol', 'yplus'
        ]
        data['solver']['reference-values'] = {
            value: re.search(
                fr'\(reference-{value}\s+([^)\s]+)\)',
                general_info
            ).group(1)
            for value in reference_values
        }

    if kwargs['mat']:
        data['materials'] = {}
        materials = re.search(
            r'(\(materials.*)',
            general_info,
            re.M
        ).group(1)
        materials: NestedStrList = stringify_nested_list(sexpdata.loads(materials))
        for material in materials[1]:
            name = material[0]
            data['materials'][name] = {}
            data['materials'][name]['type'] = material[1]
            for property_ in material[2:]:
                property_name = property_[0]
                if property_[1] == '.':
                    data['materials'][name][property_name] = property_[2]
                elif isinstance(property_value_list := property_[1], list):
                    if property_value_list[1] == '.':
                        data['materials'][name][property_name] = f'{property_value_list[0]}/{property_value_list[2]}'
                    elif property_value_list[1] == 'piecewise-linear':
                        value = [f'{p[0]}, {p[2]}' for p in property_value_list[2:]]
                        data['materials'][name][property_name] = {
                            f'{property_value_list[0]}/{property_value_list[1]}': value
                        }
                    elif property_value_list[1] in ['piecewise-polynomial', 'nasa-9-piecewise-polynomial']:
                        value = [str(p).strip('[]') for p in property_value_list[2:]]
                        data['materials'][name][property_name] = {
                            f'{property_value_list[0]}/{property_value_list[1]}': value
                        }
                    elif property_value_list[0] == 'orthotropic':
                        value = {}
                        for p in property_value_list[1:]:
                            orth_property_name = p[0]
                            if orth_property_name in ['direction-0', 'direction-1', 'direction-2']:
                                value[orth_property_name] = str(p[1:]).strip('[]')
                            elif orth_property_name in ['k0', 'k1', 'k2']:
                                value[orth_property_name] = f'{sexpdata.car(p[1])}/{sexpdata.cdr(p[1])}'
                        data['materials'][name][property_name] = {f'{property_value_list[0]}': value}
                    else:
                        value = ' '.join(str(p) for p in property_value_list[1:])
                        data['materials'][name][property_name] = f'{property_value_list[0]}/{value}'

    if kwargs['bd']:
        from .boundary import BoundaryFactory

        # get tubulence model
        if not (solver_turb := data.get('solver', {}).get('turb', None)):
            case_config = re.search(
                r'^\(case-config.*',
                general_info,
                re.M
            ).group()
            kvs = {
                m[0]: m[1]
                for m in re.findall(
                    r"\(([^()\s]+)\s+\.\s+([^()\s]+)\)",
                    case_config
                )
            }
            if kvs['rp-visc?'] == "#f":
                solver_turb = "inviscid"
            else:
                for key in [
                    'rp-lam?', 'rp-ke?', 'rp-kw?', 'rp-sa?', 'sg-rsm?',
                    'rp-les?', 'rp-des?', 'rp-kklw', 'rp-v2f?'
                ]:
                    if kvs[key] == "#t":
                        solver_turb = key[3:-1]
                        break

        data['boundary'] = {}
        boundaries: list[NestedStrList] = stringify_nested_list(sexpdata.parse(boundary_info, true=None))
        for boundary_info in boundaries:
            id_, type_, name, _ = [_ for _ in boundary_info[1]]
            new_boundary = BoundaryFactory.create(name, id_, type_)
            b_list = data['boundary'].get(type_, [])

            for property_ in filter(lambda x: len(x) > 1, boundary_info[2]):
                property_name = property_[0].replace('-', '_').replace('?', '').replace('/', '_')
                if hasattr(new_boundary, property_name):
                    if property_[1] == '.':
                        setattr(new_boundary, property_name, property_[2])
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
                            setattr(new_boundary, property_name, f'{property_[1][0]}/{property_[1][2]}')

            b_list.append(
                new_boundary.to_dict(solver_turb)
                if hasattr(new_boundary, 'to_dict')
                else new_boundary.__dict__
            )
            data['boundary'][type_] = b_list

    if kwargs['interfaces']:
        data['interfaces'] = {}
        interfaces = re.search(
            r'(\(sliding-interfaces\s+.*)',
            general_info,
            re.M
        ).group(1)
        interfaces: list[NestedStrList] = stringify_nested_list(sexpdata.loads(interfaces, true=None)[1])
        for interface in interfaces:
            name = interface[0]
            data['interfaces'][name] = {
                property_[0]: property_[2] if len(property_) == 3 else property_[1]
                for property_ in filter(lambda x: len(x) > 1, interface[1:])
            }

    if kwargs['ne']:
        data['named-expressions'] = {}
        nes = re.search(
            r'(\(named-expressions.*)',
            general_info,
            re.M
        ).group(1)
        nes: NestedStrList = stringify_nested_list(sexpdata.loads(nes, true=None)[1])
        for ne in nes:
            ne_dict = {
                property_[0]: property_[2]
                for property_ in ne
            }
            data['named-expressions'][ne_dict['name']] = ne_dict

    if kwargs['disc']:
        from .utils import DISCRETIZATION_SCHEME

        data['disc-scheme'] = {}
        disc_scheme = {
            ds[0]: DISCRETIZATION_SCHEME[ds[1]]
            for ds in re.findall(
                r'\((.*)/scheme\s+(\d+)\)',
                general_info
            )
        }
        for eq in ['flow', 'pressure', 'mom', 'temperature', 'k', 'omega', 'epsilon']:
            data['disc-scheme'][eq] = disc_scheme.get(eq)

        data['relax-factor'] = {}
        if data['disc-scheme']['flow'] == 'Coupled':
            for eq in ['pressure', 'mom']:
                data['relax-factor'][eq] = re.search(
                    fr'\(pressure-coupled/{eq}/pseudo-explicit-relax\s+([\d.]+)\)',
                    general_info
                ).group(1)
            for eq in ['temperature', 'k', 'omega', 'epsilon', 'turb-viscosity', 'density', 'body-force']:
                data['relax-factor'][eq] = re.search(
                    fr'\({eq}/pseudo-relax\s+([\d.]+)\)',
                    general_info
                ).group(1)
        else:
            relax_factor = {
                ur[0]: ur[1]
                for ur in re.findall(
                    fr'\((.*)/relax\s+([\d.]+)\)',
                    general_info
                )
            }
            for eq in ['pressure', 'mom', 'temperature', 'k', 'omega', 'epsilon', 'turb-viscosity', 'density', 'body-force']:
                data['relax-factor'][eq] = relax_factor.get(eq, '')

    if kwargs['rd']:
        data['report-definitions'] = {}
        rds = re.search(
            r'(\(monitor/report-definitions.*)',
            general_info,
            re.M
        ).group(1)
        rds: NestedStrList = stringify_nested_list(sexpdata.loads(rds, true=None)[1])
        for rd in rds:
            name = rd[0][2]
            type_ = rd[1][1]
            data['report-definitions'][name] = {'type': type_}
            if 'volume' in type_:
                data['report-definitions'][name]['field'] = rd[1][2][2]
                data['report-definitions'][name]['zones'] = [zone for zone in rd[1][6][1:]]
                data['report-definitions'][name]['per-zone?'] = rd[1][-5][2]
            elif 'surface' in type_:
                data['report-definitions'][name]['field'] = rd[1][2][2]
                data['report-definitions'][name]['surfaces'] = [surface for surface in rd[1][5][1:]]
                data['report-definitions'][name]['per-surface?'] = rd[1][-5][2]
            elif 'flux' in type_:
                data['report-definitions'][name]['zones'] = [zone for zone in rd[1][3][1:]]
                data['report-definitions'][name]['per-zone?'] = rd[1][-5][2]

    if kwargs['plotsets']:
        data['plotsets'] = {}
        plotsets = re.search(
            r'(\(monitor/plotsets.*)',
            general_info,
            re.M
        ).group(1)
        plotsets: NestedStrList = stringify_nested_list(sexpdata.loads(plotsets, true=None)[1])
        for plotset in plotsets:
            plotset_dict = {
                property_[0]: property_[2]
                for property_ in plotset
                if property_[0] not in ['old-props', 'report-defs']
            }
            plotset_dict['report-defs'] = plotset[6][1:]
            data['plotsets'][plotset_dict['name']] = plotset_dict

    if kwargs['monitorsets']:
        data['monitorsets'] = {}
        monitorsets = re.search(
            r'(\(monitor/monitorsets.*)',
            general_info,
            re.M
        ).group(1)
        monitorsets: NestedStrList = stringify_nested_list(sexpdata.loads(monitorsets, true=None)[1])
        for monitorset in monitorsets:
            monitorset_dict = {
                property_[0]: property_[2]
                for property_ in monitorset
                if property_[0] not in ['old-props', 'report-defs']
            }
            monitorset_dict['report-defs'] = monitorset[-4][1:]
            data['monitorsets'][monitorset_dict['name']] = monitorset_dict

    if kwargs['residuals']:
        data['residuals'] = {}

        for setting in [
            r'advanced-options\?', r'normalize\?', r'compute-local\?',
            r'scale\?', 'convergence-criterion-type', 'n-display',
            'n-save', r'plot\?', r'print\?', 'n-maximize-norms',
        ]:
            value = re.search(
                fr'\(residuals/{setting}\s+(#[tf]|[\d.]+)\)',
                general_info,
            ).group(1)
            data['residuals'][setting.removesuffix(r'\?')] = value
        cct = data['residuals']['convergence-criterion-type']
        data['residuals']['convergence-criterion-type'] = 'absolute' if cct == '0' else 'none'

        if not (solver_time := data.get('solver', {}).get('time', None)):
            case_config = re.search(
                r'^\(case-config.*',
                general_info,
                re.M
            ).group()
            is_unsteady = re.search(
                r"\(rp-unsteady\?\s+\.\s+([^()\s]+)\)",
                case_config
            ).group(1)
            solver_time = "transient" if is_unsteady == "#t" else "steady"
        residuals = 'residuals/settings-transient' if solver_time == 'transient' else 'residuals/settings'
        res = re.search(
            fr'(\({residuals}\s+.*)',
            general_info,
            re.M
        ).group(1)
        res = sexpdata.loads(res, true=None)[1]
        if str(res) != '#f':
            res: NestedStrList = stringify_nested_list(res)
            for eq in res:
                data['residuals'][eq[0]] = {
                    'monitor': eq[1],
                    'check-convergence': eq[3],
                    'absolute-criteria': eq[4],
                }

    if kwargs['iter']:
        data['iter'] = {}

        if not (solver_time := data.get('solver', {}).get('time', None)):
            case_config = re.search(
                r'^\(case-config.*',
                general_info,
                re.M
            ).group()
            is_unsteady = re.search(
                r"\(rp-unsteady\?\s+\.\s+([^()\s]+)\)",
                case_config
            ).group(1)
            solver_time = "transient" if is_unsteady == "#t" else "steady"

        if solver_time == 'steady':
            data['iter']['iterations'] = re.search(
                r'\(number-of-iterations\s+(\d+)\)',
                general_info
            ).group(1)
        else:
            sel = re.search(
                r'\(physical-time-step-sel\s+"([^"]+)"\)',
                general_info
            ).group(1)
            expr = re.search(
                r'\(physical-time-step-expr\s+"([^"]+)"\)',
                general_info
            ).group(1)
            data['iter']['physical-time-step'] = f'{sel}/{expr}'
            for key in ['time-steps', 'max-iters-per-step', 'time-step', 'flow-time']:
                data['iter'][key] = re.search(
                    fr'\({key}\s+(\d+)\)',
                    general_info
                ).group(1)

    if kwargs['surfaces']:
        data['surfaces'] = {}

        surfaces_groups = re.search(
            r'(\(surfaces/groups.*)',
            cortex_info,
            re.M
        ).group(1)
        surfaces_groups: NestedStrList = stringify_nested_list(sexpdata.loads(surfaces_groups, true=None)[1])
        name_id_map = {
            surface[0]: surface[1][0]
            for surface in surfaces_groups
        }  # name -> id

        surface_id_map = re.search(
            r'(\(cx-surface-id-map.*)',
            cortex_info,
            re.M
        ).group(1)
        surface_id_map: NestedStrList = stringify_nested_list(sexpdata.loads(surface_id_map, true=None)[1])
        id_virtual_id_map = {
            id_group[0]: id_group[1]
            for id_group in surface_id_map
        }  # id -> virtual id

        virtual_id_name_map = {
            id_virtual_id_map[id_]: name
            for name, id_ in name_id_map.items()
        }  # virtual id -> name

        surface_def_list = re.search(
            r'(\(cx-surface-def-list.*)',
            cortex_info,
            re.M
        ).group(1)
        surface_def_list: NestedStrList = stringify_nested_list(sexpdata.loads(surface_def_list, true=None)[1])
        for surface_def in surface_def_list:
            surface = surface_def[2]
            surface_type = surface[0]
            match surface_type:
                case 'line-surface':
                    virtual_id = surface[1]
                    data['surfaces'][virtual_id_name_map[virtual_id]] = {
                        'type': surface_type,
                        'start': surface[2],
                        'end': surface[3],
                    }
                case 'plane-surface':
                    virtual_id = surface[1]
                    data['surfaces'][virtual_id_name_map[virtual_id]] = {
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

    if kwargs['contours']:
        data['contours'] = {}
        contours = re.search(
            r'(\(graphics/contours.*)',
            general_info,
            re.M
        ).group(1)
        contours: NestedStrList = stringify_nested_list(sexpdata.loads(contours, true=None)[1])
        for contour in contours:
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
            data['contours'][contour_dict['name']] = contour_dict

    if kwargs['vectors']:
        data['vectors'] = {}
        vectors = re.search(
            r'(\(graphics/vectors\s.*)',
            general_info,
            re.M
        ).group(1)
        vectors: NestedStrList = stringify_nested_list(sexpdata.loads(vectors, true=None)[1])
        for vector in vectors:
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
            data['vectors'][vector_dict['name']] = vector_dict

    if kwargs['xy_plot']:
        data['xy-plot'] = {}
        xy_plots = re.search(
            r'(\(graphics/xy-plot.*)',
            general_info,
            re.M
        ).group(1)
        xy_plots: NestedStrList = stringify_nested_list(sexpdata.loads(xy_plots, true=None)[1])
        for xy_plot in xy_plots:
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
            data['xy-plot'][xy_plot_dict['name']] = xy_plot_dict

    return data


def extract_h5(file_path: str) -> None:
    """Extract cas.h5 general, boundary and cortex strings to files

    Parameters
    ---------
    file_path : str
        Path to the cas.h5 file
    """
    import h5py
    with h5py.File(file_path) as f:
        settings: h5py.Group = f['/settings']
        general_info = settings['Rampant Variables'][0].decode()
        boundary_info = settings['Thread Variables'][0].decode()
        cortex_info = settings['Cortex Variables'][0].decode()
    with open('general.scm', 'w', encoding='utf-8') as f:
        f.write(general_info)
    with open('boundary.scm', 'w', encoding='utf-8') as f:
        f.write(boundary_info)
    with open('cortex.scm', 'w', encoding='utf-8') as f:
        f.write(cortex_info)


def show_mesh(file_path: str) -> None:
    """Show mesh with PyVista

    Parameters
    ---------
    file_path : str
        Path to the .h5 file
    """
    import pyvista as pv
    from .plotter import MeshPlotter

    if file_path.endswith('cas.h5'):
        from .utils import disable_dat_file
        with disable_dat_file(file_path):
            mesh = pv.read(file_path)
    elif file_path.endswith('msh.h5'):
        import numpy as np
        from h5py import File, Group, Dataset

        with File(file_path) as f:
            root_group: Group = f['/meshes/1']
            dimension: np.int32 = root_group.attrs['dimension'][0]
            nodeCount: np.uint64 = root_group.attrs['nodeCount'][0]
            pv_points = np.zeros((nodeCount, 3), dtype=np.float64)

            # nodes
            zoneTopology: Group = root_group['nodes/zoneTopology']
            nZones: np.uint64 = zoneTopology.attrs['nZones'][0]
            minId: Dataset = zoneTopology['minId']
            maxId: Dataset = zoneTopology['maxId']

            coords_group: Group = root_group['nodes/coords']
            for i in range(nZones):
                pv_points[minId[i] - 1: maxId[i], :dimension] = coords_group[f'{i + 1}'][:]

            # faces
            # zoneTopology: Group = root_group['faces/zoneTopology']
            # zoneType: Dataset = faces_zone_topo['zoneType']
            faces_nodes_group: Group = root_group['faces/nodes']
            nSections: np.uint64 = faces_nodes_group.attrs['nSections'][0]

            nnodes_list, nodes_list = [], []
            for i in range(nSections):
                # if (not include_interior) and int(zoneType[i]) == 2:
                # continue
                section_group: Group = faces_nodes_group[f"{i + 1}"]
                nnodes_list.append(section_group['nnodes'][:])
                nodes_list.append(section_group['nodes'][:] - 1)

            nnodes = np.concatenate(nnodes_list)
            nodes = np.concatenate(nodes_list)
            offsets = np.cumsum(nnodes) - nnodes
            pv_faces = np.insert(nodes, offsets, nnodes)

        mesh = pv.PolyData(
            pv_points,
            faces=pv_faces if dimension == 3 else None,
            lines=pv_faces if dimension == 2 else None,
        )

    plotter = MeshPlotter(mesh, locals().get('dimension'))
    plotter.show(title=file_path)


def plot(file_path: str, out: bool = False, xy: bool = False, dat: bool = False) -> None:
    """Plot Ansys Fluent export data files

    Parameters
    ---------
    file_path : str
        Path to the data file
    out : bool
        If True, plot .out data file
    xy : bool
        If True, plot .xy data file
    dat : bool
        If True, plot .dat.h5 residuals data
    """
    import re
    import numpy as np
    import matplotlib.pyplot as plt

    pattern = re.compile(r'"([^"]*)"')

    def plot_out(file_path: str) -> None:
        with open(file_path, encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                match line_num:
                    case 1:
                        title = re.findall(pattern, line)[0]
                    case 2:
                        _, *report_definitions = re.findall(pattern, line)
                    case 3:
                        xlabel, *ylabels = re.findall(pattern, line)
                    case _:
                        break

        data = np.loadtxt(file_path, skiprows=3)
        plt.figure()
        plt.plot(data[:, 0], data[:, 1:])
        plt.title(title)
        plt.xlabel(xlabel)
        plt.legend(ylabels)
        plt.grid()
        plt.show()

    def plot_xy(file_path: str) -> None:
        with open(file_path, encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                match line_num:
                    case 1:
                        title = re.findall(pattern, line)[0]
                    case 2:
                        x_axis_title, y_axis_title = re.findall(pattern, line)
                    case _:
                        content = f.read()
                        break
        chunks = content.split('((xy/key/label "')[1:]
        data = {}
        for chunk in chunks:
            label, rest = chunk.split('"', 1)
            first_bracket = rest.find(")")
            last_bracket = rest.rfind(")")
            data_str = rest[first_bracket + 1: last_bracket]
            arr_2d = np.fromstring(data_str, dtype=np.float64, sep=" ").reshape(-1, 2)
            data[label] = arr_2d[arr_2d[:, 0].argsort()]

        plt.figure()
        for label, arr_2d in data.items():
            plt.plot(arr_2d[:, 0], arr_2d[:, 1], label=label)
        plt.title(title)
        plt.xlabel(x_axis_title)
        plt.ylabel(y_axis_title)
        plt.legend()
        plt.grid()
        plt.show()

    def plot_dat(file_path: str) -> None:
        from h5py import File, Group

        data = {}

        with File(file_path) as f:
            residuals: Group = f['/results/residuals']
            for phase_name, phase_group in residuals.items():
                data[phase_name] = {}
                for eq_name, eq_group in phase_group.items():
                    data[phase_name][eq_name] = {
                        'data': eq_group['data'][:, 0] / eq_group['data'][:, 1],
                        'iterations': eq_group['iterations'][:]
                    }
        phase_num = len(data)

        plt.figure()
        for i, (phase_name, phase_dict) in enumerate(data.items(), start=1):
            plt.subplot(1, phase_num, i)
            for eq_name, eq_dict in phase_dict.items():
                plt.plot(eq_dict['iterations'], eq_dict['data'], label=eq_name)
            plt.xlabel('iterations')
            plt.ylabel('residuals')
            plt.yscale('log')
            plt.title(phase_name)
            plt.legend()
            plt.grid()
        plt.show()

    if out:
        plot_out(file_path)
    elif xy:
        plot_xy(file_path)
    elif dat:
        plot_dat(file_path)
    else:
        file_ext = file_path.split('.')[-1]
        if file_ext == 'out':
            plot_out(file_path)
        elif file_ext == 'xy':
            plot_xy(file_path)
        elif file_path.endswith('.dat.h5'):
            plot_dat(file_path)
        else:
            raise ValueError("Please specify --out, --xy or --dat")


def plot_data(file_path: str):
    """Visualize Fluent .cas.h5 + .dat.h5 solution data with interactive cross-sections.

    Uses PyVista's built-in VTK FLUENTCFF Reader to load both mesh and solution data
    from .cas.h5 and .dat.h5 files. Provides an interactive plane widget for creating
    cross-sections (slices) with selectable field variables and color mapping.

    Parameters
    ----------
    file_path : str
        Path to the .cas.h5 file. The corresponding .dat.h5 file must be in the same
        directory with the same base name (e.g. ``case.cas.h5`` -> ``case.dat.h5``).
    """
    import os
    import pyvista as pv
    from .plotter import DataPlotter

    if not os.path.exists(file_path.replace('.cas.h5', '.dat.h5')):
        print("No .dat.h5 file found.")
        print("Make sure the .dat.h5 file exists alongside the .cas.h5 file.")
        return

    mesh = pv.read(file_path)
    var_names = (
        'SV_P',
        'SV_T',
        'SV_DENSITY',
        'SV_U', 'SV_V', 'SV_W',
        'SV_H',
    )
    print(f"{len(var_names)} variable(s) available:")
    for i, name in enumerate(var_names):
        print(f"    [{i}] {name}")

    plotter = DataPlotter(mesh, var_names)
    plotter.show(title=file_path)


def main() -> None:
    import argparse

    BANNER = r"""
        ________      _
  _____/ __/ __/   __(_)__ _      __
 / ___/ /_/ /_| | / / / _ \ | /| / /
/ /__/ __/ __/| |/ / /  __/ |/ |/ /
\___/_/ /_/   |___/_/\___/|__/|__/

A Python CLI tool to inspect Ansys Fluent .cas.h5/.msh.h5/.dat.h5 files without opening Fluent
"""

    parser = argparse.ArgumentParser(
        prog='cffview',
        description=BANNER,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "file_path",
        type=str,
        help="path to the input file",
    )
    parser.add_argument(
        "--save",
        nargs="?",
        default=False,
        metavar="OUTPUT_FILE_NAME",
        help="output file name (if not specified, the same as the input file)",
    )

    ARGUMENTS = [
        (("--version",), "show the version of the .h5 file"),
        (("--extract",), "extract cas.h5 general and boundary string to files"),
        (("--mesh", "--showmesh",), "show mesh using pyvista"),
        (("--data", "--plotdata",), "plot data using pyvista"),
        (("--solver",), "show solver settings"),
        (("--mat", "--materials"), "show materials settings"),
        (("--bd", "--boundary"), "show boundary settings"),
        (("--interfaces",), "show mesh interfaces settings"),
        (("--ne", "--named-expressions"), "show named-expressions settings"),
        (("--disc",), "show disc-scheme and relax-factor settings"),
        (("--rd", "--report-definitions"), "show report-definitions settings"),
        (("--plotsets",), "show report-definitions plotsets settings"),
        (("--monitorsets",), "show report-definitions monitorsets settings"),
        (("--residuals",), "show residuals settings"),
        (("--iter",), "show iteration settings"),
        (("--surfaces",), "show surfaces settings"),
        (("--contours",), "show graphics contours settings"),
        (("--vectors",), "show graphics vectors settings"),
        (("--xy-plot",), "show graphics xy-plot settings"),
        (("--plot",), "plot data file, support --out and --xy, if not specified, infer from file extension"),
        (("--out",), "plot .out file, used with --plot"),
        (("--xy",), "plot .xy file, used with --plot"),
        (("--dat",), "plot .dat.h5 file's residuals, used with --plot"),
    ]
    for flags, help_text in ARGUMENTS:
        parser.add_argument(*flags, action="store_true", help=help_text)

    args = parser.parse_args()

    if not args.file_path.endswith((".cas.h5", ".msh.h5")) and not args.plot:
        print("Invalid arguments.")
        print("Please provide a .cas.h5 or .msh.h5 file or add --plot argument to plot outfile")
        return

    if args.version:
        print_version(args.file_path)
    elif args.extract:
        extract_h5(args.file_path)
    elif args.file_path.endswith(".msh.h5"):
        show_mesh(args.file_path)
    elif args.file_path.endswith(".cas.h5"):
        if args.mesh:
            show_mesh(args.file_path)
        elif args.data:
            plot_data(args.file_path)
        else:
            from .utils import print_colored_dict
            keys = [
                'solver', 'mat', 'bd', 'ne', 'disc', 'rd', 'interfaces',
                'plotsets', 'monitorsets', 'residuals', 'iter', 'surfaces',
                'contours', 'vectors', 'xy_plot',
            ]
            kwargs = {k: getattr(args, k) for k in keys}
            output = read_case(args.file_path, **kwargs)
            print_colored_dict(output)

            if args.save is not False:
                import json
                save_name = args.save if args.save else args.file_path
                with open(f"{save_name}.json", "w", encoding="utf-8") as f:
                    json.dump(output, f, ensure_ascii=False, indent=4)
    elif args.plot:
        plot(args.file_path, out=args.out, xy=args.xy, dat=args.dat)
