[![PyPI](https://img.shields.io/pypi/v/cffview.svg?logo=python&logoColor=white)](https://pypi.org/project/cffview/)
[![Python versions](https://img.shields.io/pypi/pyversions/cffview.svg?color=orange&logo=python&label=python&logoColor=white)](https://pypi.org/project/cffview)
[![CI](https://github.com/preamer/cffview/actions/workflows/build_wheels.yml/badge.svg)](https://github.com/preamer/cffview/actions/workflows/build_wheels.yml)

[中文](README.zh.md)

# cffview

A command-line tool for inspecting Ansys Fluent `.cas.h5` / `.msh.h5` files **without opening Fluent**.

- Read solver settings, materials, boundary conditions, discretisation schemes, and more directly from the HDF5 file.
- Visualise the mesh with [PyVista](https://pyvista.org).

---

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

---

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
| `--showmesh` | Visualise the mesh interactively with PyVista |
| `--solver` | Solver type, time, dimension, precision, turbulence model, energy, radiation, gravity |
| `--mat` | Material properties |
| `--bd` | Boundary condition settings |
| `--ne` | Named expressions |
| `--disc` | Discretisation schemes and relaxation factors |
| `--rd` | Report definitions |
| `--plotsets` | Plot sets |
| `--monitorsets` | Monitor sets |
| `--iter` | Iteration / time-step settings |
| `--contours` | Graphics contours settings |
| `--vectors` | Graphics vectors settings |
| `--save` | Save the output to `<file>.json` |

Multiple flags can be combined freely. Case settings flags (`--solver`, `--mat`, etc.) apply to `.cas.h5` files only.

### Examples

```bash
# Show all settings and save to JSON
cffview case.cas.h5 --save

# Show solver configuration and boundary conditions
cffview case.cas.h5 --solver --bd

# Visualise the mesh
cffview case.cas.h5 --showmesh
cffview mesh.msh.h5 --showmesh

# Check the Fluent version of file
cffview case.cas.h5 --version

# Extract raw Scheme strings for manual inspection
cffview case.cas.h5 --extract
```

### Demo

[demo.webm](https://github.com/user-attachments/assets/9047a354-b5cb-475e-b030-97609e2a1274)

---

## License

[BSD-3-Clause](LICENSE)
