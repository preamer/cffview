# Examples

Sample files for understanding and testing cffview's parsing and plotting
logic. The `*.scm` files are the raw Scheme text stored in the `/settings`
group of a real Ansys Fluent `.cas.h5` case (dumped with
`cffview --extract`); the `*.xy` / `*.out` files are Fluent export data for
the plotting paths.

> [!NOTE]
> Only tested with Ansys Fluent 25R2.

## Scheme files (`*.scm`)

Fluent stores case settings as Scheme S-expressions. The corresponding
readers in `src/cffview/reader.py` parse these into readable settings:

| File | Source in the case | cffview option | Contents |
|---|---|---|---|
| `general.scm` | `/settings/Rampant Variables` | `--solver`, `--mat`, `--solution`, `--rd`, `--plotsets`, `--monitorsets`, `--residuals`, `--iter`, `--contours`, `--vectors`, `--pathlines`, `--xy-plot`, ... | Full solver settings; source of most sections below |
| `case-config.scm` | `(case-config ...)` inside Rampant Variables | `--solver` | Solver configuration block (segregated/coupled, steady/transient, dimension, turbulence/radiation models...) |
| `context.scm` | `(context/map-r17+ ...)` inside Rampant Variables | — | Multi-line context variables (internal solver settings) |
| `materials.scm` | `(materials ...)` inside Rampant Variables | `--mat` | Material properties (density, specific heat, conductivity...) |
| `boundary.scm` | `/settings/Thread Variables` | `--bd` | Boundary condition settings for every zone |
| `sliding-interfaces.scm` | `(sliding-interfaces ...)` inside Rampant Variables | `--interfaces` | Sliding / mesh interfaces |
| `named-expression.scm` | `(named-expressions ...)` inside Rampant Variables | `--ne` | Named expressions |
| `monitor-report-definitions.scm` | `(monitor/report-definitions ...)` inside Rampant Variables | `--rd` | Report definitions |
| `plotsets.scm` | `(monitor/plotsets ...)` inside Rampant Variables | `--plotsets` | Plot sets |
| `monitorsets.scm` | `(monitor/monitorsets ...)` inside Rampant Variables | `--monitorsets` | Monitor sets |
| `residuals.scm` | `(residuals ...)` inside Rampant Variables | `--residuals` | Residual settings |
| `contours.scm` | `(graphics/contours ...)` inside Rampant Variables | `--contours` | Graphics contour definitions |
| `vectors.scm` | `(graphics/vectors ...)` inside Rampant Variables | `--vectors` | Graphics vector definitions |
| `pathlines.scm` | `(graphics/pathlines ...)` inside Rampant Variables | `--pathlines` | Graphics pathline definitions |
| `xy-plot.scm` | `(graphics/xy-plot ...)` inside Rampant Variables | `--xy-plot` | Graphics XY-plot definitions |
| `cortex.scm` | `/settings/Cortex Variables` | `--surfaces`, `--cff`, `--units` | GUI state: reference frames, scenes, surfaces, cell functions, unit table |
| `surfaces.scm` | `(surfaces/groups ...)` inside Cortex Variables | `--surfaces` | User-defined surface groups and definitions |
| `cell-function-defs.scm` | `(cell-function-defs ...)` inside Cortex Variables | `--cff` | Custom field function definitions (`name` + `display` expression) |
| `unit-table.scm` | `(unit-table ...)` inside Cortex Variables | `--units` | Unit table (`quantity unit scale offset`); absent = default SI |
| `tgrid.scm` | `/settings/TGrid Variables` | `--extract` | Meshing parameters (Fluent Meshing), not used by `read_case` |

## Plot data files

| File | cffview option | Contents |
|---|---|---|
| `1p-ps40.xy` | `--plot xy` | Fluent XY-plot export (title, axis titles, per-curve data) |
| `mass-rfile.out` | `--plot out` | Fluent report output file (report definitions + data) |

## How they were generated

The `*.scm` files are produced by running `cffview --extract` on a case file,
which dumps the raw Scheme strings of `/settings/Rampant Variables`,
`/settings/Thread Variables` and `/settings/Cortex Variables`:

```bash
cffview your_case.cas.h5 --extract   # writes general.scm, boundary.scm, cortex.scm
```

The smaller `*.scm` files (e.g. `materials.scm`, `contours.scm`) are extracted
sub-blocks of these, kept separate for easier inspection and for testing
individual readers.

## Using them for development

- Each reader in `reader.py` can be exercised standalone with a synthetic
  `CaseTexts`, e.g. `_read_units(CaseTexts(cortex=open('unit-table.scm').read()))`
- The plot paths accept the export files directly:
  `cffview examples/1p-ps40.xy --plot` or `cffview examples/mass-rfile.out --plot`
