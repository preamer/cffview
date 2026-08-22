"""Command-line interface for cffview.

Entry point of the ``cffview`` console script: parses CLI arguments, prints
the Fluent version, extracts raw Scheme strings, plots data files, and
visualises meshes or data with PyVista. Reading case settings is delegated
to :func:`cffview.reader.read_case`.
"""


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
        import os
        dat_path = os.path.splitext(file_path)[0]
        if dat_path.endswith('.cas'):
            dat_path = dat_path[:-4]
        dat_path += '.dat.h5'
        bak_path = dat_path + '.tmp_bak'
        renamed = os.path.exists(dat_path)
        if renamed:
            os.rename(dat_path, bak_path)
        try:
            mesh = pv.read(file_path)
        finally:
            if renamed and os.path.exists(bak_path):
                os.rename(bak_path, dat_path)
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

A Python CLI tool to view Ansys Fluent .cas.h5/.msh.h5/.dat.h5 files without opening Fluent
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
        (("--cff", "--custom-field-functions"), "show custom field functions"),
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
    ]
    for flags, help_text in ARGUMENTS:
        parser.add_argument(*flags, action="store_true", help=help_text)
    parser.add_argument(
        "--units",
        nargs="*",
        default=False,
        metavar="KEYWORD",
        help="show unit table, optionally filtered by one or more keywords",
    )
    parser.add_argument(
        "--save",
        nargs="?",
        default=False,
        metavar="OUTPUT_FILE_NAME",
        help="output file name (if not specified, the same as the input file)",
    )
    parser.add_argument(
        "--plot",
        nargs="?",
        const=True,
        default=False,
        metavar="TYPE",
        help="plot data file; TYPE is one of 'out', 'xy', 'dat' (inferred from the file extension when omitted)",
    )

    args = parser.parse_args()

    if not args.file_path.endswith((".cas.h5", ".msh.h5")) and args.plot is False:
        parser.error("Invalid arguments, please provide a .cas.h5 or .msh.h5 file or add --plot argument to plot file")

    if args.version:
        print_version(args.file_path)
    elif args.extract:
        extract_h5(args.file_path)
    elif args.plot:
        plot(
            args.file_path,
            out=args.plot == 'out',
            xy=args.plot == 'xy',
            dat=args.plot == 'dat',
        )
    elif args.file_path.endswith(".msh.h5"):
        show_mesh(args.file_path)
    elif args.file_path.endswith(".cas.h5"):
        if args.mesh:
            show_mesh(args.file_path)
        elif args.data:
            plot_data(args.file_path)
        else:
            from .utils import print_colored_dict
            from .reader import read_case, READERS
            kwargs = {k: getattr(args, k) for k in READERS.keys()}
            if args.units is not False:
                kwargs['units'] = True
            output = read_case(args.file_path, **kwargs)
            if isinstance(args.units, list) and args.units:
                keywords = [k.lower() for k in args.units]
                output['units'] = {
                    name: value
                    for name, value in output['units'].items()
                    if any(
                        k in name.lower() or k in str(value[0]).lower()
                        for k in keywords
                    )
                }
            print_colored_dict(output)

            if args.save is not False:
                import json
                save_name = args.save if args.save else args.file_path
                with open(f"{save_name}.json", "w", encoding="utf-8") as f:
                    json.dump(output, f, ensure_ascii=False, indent=4)
