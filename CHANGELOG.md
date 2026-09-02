# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `--convergencesets` for showing convergence sets definitions.
- `--cell` and `--cell-registers` for showing cell registers definitions.

## [v0.5.1] - 2026-09-01

### Added

- `--pathlines` for showing graphics pathlines settings.
- `--mesh` and `--scene` for showing graphics mesh / scene settings.
- `iso-surface` and `iso-clip-new` surface types to the `--surfaces` output.
- `Time Scale Factor` to the `--solution` output when the Coupled scheme's pseudo time method is enabled.
- Full properties for `pressure-far-field` boundary (momentum / thermal / radiation groups).
- Pseudo time step settings (method, time step / time-scale-factor, length-scale method, verbosity) to the `--iter` output.
- `reporting-interval`, `update-interval` and `save-steady-statistics` to the `--iter` output.

### Changed

- Visualisation flags renamed: `--mesh`/`--showmesh` -> `--plotmesh`, `--data` -> `--plotdata`.

### Fixed

- Pseudo time method detection now uses the `dt-method` code instead of `user-defined-settings?`.
- `average-over-state` value for `single-val-expression` report definitions.

## [v0.5.0] - 2026-08-29

### Added

- Display `mesh_info` for `MeshPlotter`.
- `pseudo-time-courant-number` to the `--solution` output when the pseudo time method is enabled.
- `multi-phase` model to the `--solver` output.

### Changed

- `--disc` renamed to `--solution`; output reorganised into `solution-methods` (discretisation schemes, gradient, pseudo time method) and `solution-controls` (relaxation factors).
- `--bd` boundary output grouped into `momentum` / `thermal` / `radiation` sub-objects (fields tagged via dataclass metadata).
- Python requirement raised to `>=3.12`.

### Fixed

- Relax factors for `density`, `body-force`, `disco` when SIMPLE flow scheme pseudo time method is enabled.
- 2D `.dat.h5` plotting by removing `SV_W` from `var_names`.

## [v0.4.4] - 2026-08-24

### Added

- `flow-scheme` and `pseudo-time-method` (Off / Global Time Step / Local Time Step) to the `--solver` output.
- Gradient method (Least Squares Cell-Based / Green-Gauss Cell-Based / Green-Gauss Node-Based) to the `--disc` output.

### Fixed

- `--disc` relaxation factors are now read from `dual-ts-implicit-relax` when the pseudo time method (local time stepping) is enabled.

## [v0.4.3] - 2026-08-22

### Fixed

- `source_terms` parsing error for `Solid` and `Fluid` boundary.

## [v0.4.2] - 2026-08-22

### Added

- `--cff` / `--custom-field-functions` for showing custom field functions defined in the Cortex Variables.
- `--units [KEYWORD ...]` for showing the unit table, optionally filtered by one or more keywords; an empty table means the default SI unit system.
- `average-over-state` and `iter-range` values for `--report-definitions`.
- Mass flow rate / mass flux fields (`flow-spec`, `mass-flux`, ...) for mass-flow inlet and outlet boundaries.

### Changed

- `--plot` now takes an optional mode argument (`--plot out|xy|dat`); the standalone `--out` / `--xy` / `--dat` flags were removed, and the mode is inferred from the file extension when omitted.

## [v0.4.1] - 2026-08-18

### Added

- `--dat` for plotting `.dat.h5` file's residuals data used with `--plot`. 
- Radiation boundary condition settings (`radiation-bc`, `in-emiss`, `t-b-b-spec`, ...) for inlet/outlet boundaries and walls, shown only when a radiation model is enabled.
- `RADIATION_BC` and `T_B_B_SPEC` constants mapping Fluent radiation codes to readable strings.

### Changed

- Boundary `to_dict()` now also takes the radiation model and omits radiation-related fields when no radiation model is used.
- `MassFlowInlet` fields reorganised; turbulence parameters filtered according to the turbulence model.
- `DataPlotter` switches variables with the slider by updating the existing actors in place instead of rebuilding them, removing the UI stutter when changing variables.

### Fixed

- `source_terms` udf parsing error for `Solid` and `Fluid` boundary
- Typo in `Interior` attribute name (`is_not_a_res_lans_interface` → `is_not_a_rans_les_interface`)

## [v0.4.0] - 2026-08-14

### Added

- `--out` and `--xy` for plotting corresponding data files used with `--plot`.
- `--surfaces` for showing surfaces settings.
- Add the functionality to extract cortex_info to the extract_h5 function.
- `--data` and `--plotdata` for visualising `.dat.h5` file.

### Changed

- Refactor plotter function with `MeshPlotter` and `DataPlotter`.

### Removed

- Original `--xy` for showing graphics xy-plot settings is removed, please use `--xy-plot`. 

## [v0.3.6] - 2026-08-11

### Added

- Periodic boundary condition.
- `--interfaces` for mesh interfaces settings.
- Some const variables of Ansys Fluent.

### Fixed

- Increase line_width to make 2D `.msh.h5` mesh clearer.

### Changed

- Refactor faces parsing logic in reading `.msh.h5` mesh files.
- Use the file_path as the title of plotter window.
- Change `--save` parameter to accept parameter as output file name.
