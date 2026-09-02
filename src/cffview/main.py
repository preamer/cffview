"""Command-line interface for cffview.

Entry point of the ``cffview`` console script: parses CLI arguments and
dispatches to :mod:`cffview.extract` (version / raw Scheme export),
:mod:`cffview.plot` (matplotlib plots of Fluent export data),
:mod:`cffview.plotter` (PyVista mesh and data visualisation) and
:func:`cffview.reader.read_case` (case settings). This module only wires
the CLI together; the actual work lives in the feature modules.
"""

import glob
import argparse


def _expand_path(file_path: str) -> str:
    """Resolve a glob pattern to the first matching file (or the path as-is).

    Parameters
    ----------
    file_path : str
        Path or glob pattern (e.g. ``*.cas.h5``).

    Returns
    -------
    str
        The first matching path when ``file_path`` is a pattern with
        matches; otherwise ``file_path`` unchanged.
    """
    matches = sorted(glob.glob(file_path))
    return matches[0] if matches else file_path


def main() -> None:
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
        (("--plotmesh",), "show mesh using pyvista"),
        (("--plotdata",), "plot data using pyvista"),
        (("--solver",), "show solver settings"),
        (("--mat", "--materials"), "show materials settings"),
        (("--bd", "--boundary"), "show boundary settings"),
        (("--interfaces",), "show mesh interfaces settings"),
        (("--mesh",), "show mesh settings"),
        (("--ne", "--named-expressions"), "show named-expressions settings"),
        (("--cff", "--custom-field-functions"), "show custom field functions"),
        (("--solution",), "show solution methods and controls settings"),
        (("--rd", "--report-definitions"), "show report-definitions settings"),
        (("--residuals",), "show residuals settings"),
        (("--monitorsets",), "show report-definitions monitorsets settings"),
        (("--plotsets",), "show report-definitions plotsets settings"),
        (("--convergencesets",), "show convergencesets settings"),
        (("--cell", "--cell-registers"), "show cell-registers settings"),
        (("--iter",), "show iteration settings"),
        (("--surfaces",), "show surfaces settings"),
        (("--contours",), "show graphics contours settings"),
        (("--vectors",), "show graphics vectors settings"),
        (("--pathlines",), "show graphics pathlines settings"),
        (("--scene",), "show scene settings"),
        (("--xy-plot",), "show graphics xy-plot settings"),
    ]
    for flags, help_text in ARGUMENTS:
        parser.add_argument(*flags, action="store_true", help=help_text)
    parser.add_argument(
        "--units",
        nargs="*",
        default=False,
        metavar="KEYWORD",
        help="show changed units(default SI), optionally filtered by one or more keywords",
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

    args.file_path = _expand_path(args.file_path)

    if not args.file_path.endswith((".cas.h5", ".msh.h5")) and args.plot is False:
        parser.error("Invalid arguments, please provide a .cas.h5 or .msh.h5 file or add --plot argument to plot file")

    if args.version:
        from .extract import print_version
        print_version(args.file_path)
    elif args.extract:
        from .extract import extract_h5
        extract_h5(args.file_path)
    elif args.plot:
        from .plot import plot
        plot(
            args.file_path,
            out=args.plot == 'out',
            xy=args.plot == 'xy',
            dat=args.plot == 'dat',
        )
    elif args.file_path.endswith(".msh.h5"):
        from .plotter import plot_mesh
        plot_mesh(args.file_path)
    elif args.file_path.endswith(".cas.h5"):
        if args.plotmesh:
            from .plotter import plot_mesh
            plot_mesh(args.file_path)
        elif args.plotdata:
            from .plotter import plot_data
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
