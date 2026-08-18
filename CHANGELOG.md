# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
