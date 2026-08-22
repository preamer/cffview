[![PyPI](https://img.shields.io/pypi/v/cffview.svg?logo=python&logoColor=white)](https://pypi.org/project/cffview/)
[![Python versions](https://img.shields.io/pypi/pyversions/cffview.svg?color=orange&logo=python&label=python&logoColor=white)](https://pypi.org/project/cffview)
[![CI](https://github.com/preamer/cffview/actions/workflows/build_wheels.yml/badge.svg)](https://github.com/preamer/cffview/actions/workflows/build_wheels.yml)

[中文](README.zh.md)

# cffview

> CFF is an abbreviation for Ansys **C**ommon **F**luids **F**ormat.

A command-line tool for viewing Ansys Fluent `.cas.h5` / `.msh.h5` / `.dat.h5` files **without opening Fluent**.

- Read solver settings, materials, boundary conditions, discretisation schemes, and more directly from the HDF5 file.
- Visualise mesh or data with [PyVista](https://pyvista.org).

## Installation

### PyPI

```bash
pip install cffview
```

### From source

```bash
git clone https://github.com/preamer/cffview.git
cd cffview
pip install .
```

## Usage

> [!IMPORTANT]
> Only tested with Ansys Fluent 25R2!

```
cffview <file> [options]
```

### Options

| Option | Description |
|---|---|
| `--version` | Print the Fluent version of file |
| `--extract` | Dump raw Scheme settings to `general.scm` and `boundary.scm` |
| `--mesh`, `--showmesh` | Visualise the mesh interactively with PyVista |
| `--data`, `--plotdata` | Plot the data interactively with PyVista (may not work, depending on `vtkFLUENTCFFReader`) |
| `--solver` | Solver type, time, dimension, precision, turbulence model, energy, radiation, gravity |
| `--mat`, `--materials` | Material properties |
| `--bd`, `--boundary` | Boundary condition settings |
| `--interfaces` | Mesh interfaces settings |
| `--ne`, `--named-expressions` | Named expressions |
| `--cff`, `--custom-field-functions` | Custom field functions |
| `--units [KEYWORD ...]` | Unit table (filtered by one or more keywords; empty means default SI units) |
| `--disc` | Discretisation schemes and relaxation factors |
| `--rd`, `--report-definitions` | Report definitions |
| `--plotsets` | Plot sets |
| `--monitorsets` | Monitor sets |
| `--residuals` | Residual settings |
| `--iter` | Iteration / time-step settings |
| `--surfaces` | Surfaces settings |
| `--contours` | Graphics contours settings |
| `--vectors` | Graphics vectors settings |
| `--xy-plot` | Graphics xy-plot settings |
| `--save` | Save the output to `file_name.json` (if `file_name` not specified, it is the same as input file) |
| `--plot` | plot data file, support `--out` and `--xy`, if not specified, infer from file extension |
| `--out` | plot `.out` file, used with `--plot` |
| `--xy` | plot `.xy` file, used with `--plot` |
| `--dat` | plot `.dat.h5` file's residuals data, used with `--plot` |

Multiple flags can be combined freely. Case settings flags (`--solver`, `--mat`, etc.) apply to `.cas.h5` files only.

> [!TIP]
> Long options can be abbreviated to any unambiguous prefix. For example,
> `--inter` works for `--interfaces` and `--so` for `--solver`. An ambiguous
> prefix (e.g. `--i`, which could match `--interfaces` or `--iter`) is
> rejected with an error.

### Examples

```bash
# Show all settings and save to JSON
cffview case.cas.h5 --save

# Show solver configuration and boundary conditions
cffview case.cas.h5 --solver --bd

# Visualise the mesh
cffview case.cas.h5 --mesh
cffview mesh.msh.h5

# Visualise the data
cffview case.cas.h5 --data

# Check the Fluent version of file
cffview case.cas.h5 --version

# Extract raw Scheme strings for manual inspection
cffview case.cas.h5 --extract
```

### Demo

https://github.com/user-attachments/assets/7f97b559-87fa-4822-be9f-4e82b8c5cab6

## License

[BSD-3-Clause](LICENSE)
