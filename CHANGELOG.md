# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v0.3.6] - 2026-08-11

### Added

- Periodic boundary condition
- `--interfaces` for mesh interfaces settings
- Some const variables of Ansys Fluent

### FIxed

- Increase line_width to make 2D `.msh.h5` mesh clearer

### Changed

- Refactor faces parsing logic in reading `.msh.h5` mesh files
- Use the file_path as the title of plotter window
- Change `--save` parameter to accept parameter as output file name
