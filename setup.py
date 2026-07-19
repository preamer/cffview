"""
Build script for fv.mesh_reader (pybind11 + HDF5).

HDF5 detection order (highest to lowest priority):
  1. HDF5_DIR environment variable
  2. Local project include/ and lib/ directories
  3. pkg-config  (Linux / macOS)
  4. Conda active environment  (all platforms)
  5. Homebrew     (macOS)
  6. Common system paths  (Linux)

If detection fails, set HDF5_DIR:
  Windows : set  HDF5_DIR=C:\\path\\to\\hdf5
  Linux   : export HDF5_DIR=/path/to/hdf5
  macOS   : export HDF5_DIR=$(brew --prefix hdf5)
"""

import os
import sys
import warnings
import subprocess
from pathlib import Path

import pybind11
import numpy as np
from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext


# ---------------------------------------------------------------------------
# HDF5 detection helpers
# ---------------------------------------------------------------------------

def _pkg_config(pkg: str, flag: str) -> list[str]:
    """Run pkg-config and return parsed values, or [] on failure."""
    try:
        out = subprocess.check_output(
            ["pkg-config", flag, pkg],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        prefix = {
            "--cflags-only-I": "-I",
            "--libs-only-L": "-L",
            "--libs-only-l": "-l",
        }[flag]
        return [t[len(prefix):] for t in out.split() if t.startswith(prefix)]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def _probe_pkg_config() -> tuple[list, list, list]:
    """Try pkg-config for hdf5 / hdf5-serial; return (includes, libdirs, libs)."""
    for pkg in ("hdf5", "hdf5-serial"):
        incs = _pkg_config(pkg, "--cflags-only-I")
        ldirs = _pkg_config(pkg, "--libs-only-L")
        libs = _pkg_config(pkg, "--libs-only-l")
        if incs or ldirs:
            return incs, ldirs, libs or ["hdf5"]
    return [], [], []


def _has_hdf5_header(d: Path) -> bool:
    return (d / "hdf5.h").exists()


def find_hdf5() -> tuple[list, list, list, list, list]:
    """Returns (include_dirs, library_dirs, libraries, define_macros, extra_link_args)."""
    include_dirs: list[str] = []
    library_dirs: list[str] = []
    libraries:    list[str] = ["hdf5"]
    define_macros:   list = []
    extra_link_args: list = []

    # 1. HDF5_DIR environment variable (highest priority)
    hdf5_dir = os.environ.get("HDF5_DIR", "").strip()
    if hdf5_dir:
        p = Path(hdf5_dir)
        if (p / "include").is_dir():
            include_dirs.append(str(p / "include"))
        if (p / "lib").is_dir():
            library_dirs.append(str(p / "lib"))

    # 2. Local project include/ lib/ (bundled HDF5)
    local_inc, local_lib = Path("include"), Path("lib")
    if _has_hdf5_header(local_inc):
        include_dirs.append(str(local_inc))
    if local_lib.is_dir() and any(local_lib.iterdir()):
        library_dirs.append(str(local_lib))

    # 3. Platform-specific detection
    if sys.platform == "win32":
        define_macros.append(("H5_BUILT_AS_DYNAMIC_LIB", None))

        # Conda (most common on Windows)
        conda_base = Path(sys.prefix) / "Library"
        if _has_hdf5_header(conda_base / "include"):
            include_dirs.append(str(conda_base / "include"))
            library_dirs.append(str(conda_base / "lib"))

        # vcpkg default install
        for triplet in ["x64-windows", "x64-windows-static"]:
            vcpkg = Path(r"C:\vcpkg\installed") / triplet
            if _has_hdf5_header(vcpkg / "include"):
                include_dirs.append(str(vcpkg / "include"))
                library_dirs.append(str(vcpkg / "lib"))
                break

    elif sys.platform.startswith("linux"):
        # pkg-config (most reliable on Linux — handles Ubuntu hdf5-serial etc.)
        pkg_inc, pkg_lib, pkg_libs = _probe_pkg_config()
        include_dirs.extend(pkg_inc)
        library_dirs.extend(pkg_lib)
        if pkg_libs:
            libraries = pkg_libs

        # Ubuntu/Debian fallback: libhdf5-dev uses non-standard paths
        for candidate in [
            Path("/usr/include/hdf5/serial"),
            Path("/usr/include/hdf5"),
            Path("/usr/include"),
        ]:
            if _has_hdf5_header(candidate) and str(candidate) not in include_dirs:
                include_dirs.append(str(candidate))
                break

        for candidate in [
            Path("/usr/lib/x86_64-linux-gnu/hdf5/serial"),
            Path("/usr/lib/aarch64-linux-gnu/hdf5/serial"),
            Path("/usr/lib/hdf5/serial"),
            Path("/usr/lib64"),
        ]:
            if candidate.is_dir() and str(candidate) not in library_dirs:
                library_dirs.append(str(candidate))
                break

        # Conda on Linux
        conda_inc = Path(sys.prefix) / "include"
        conda_lib = Path(sys.prefix) / "lib"
        if _has_hdf5_header(conda_inc) and str(conda_inc) not in include_dirs:
            include_dirs.append(str(conda_inc))
            library_dirs.append(str(conda_lib))

        # rpath: embed at link time so libhdf5 is found at runtime without LD_LIBRARY_PATH
        local_has_hdf5 = bool(list(local_lib.glob("libhdf5*.so*")))
        if local_has_hdf5:
            # bundled alongside the extension module
            extra_link_args.append("-Wl,-rpath,$ORIGIN")
        else:
            for ldir in library_dirs:
                extra_link_args.append(f"-Wl,-rpath,{ldir}")

    elif sys.platform == "darwin":
        pkg_inc, pkg_lib, pkg_libs = _probe_pkg_config()
        include_dirs.extend(pkg_inc)
        library_dirs.extend(pkg_lib)
        if pkg_libs:
            libraries = pkg_libs

        # Homebrew (Apple Silicon: /opt/homebrew, Intel: /usr/local)
        for brew_prefix in [Path("/opt/homebrew"), Path("/usr/local")]:
            hdf5_prefix = brew_prefix / "opt" / "hdf5"
            if _has_hdf5_header(hdf5_prefix / "include"):
                inc = str(hdf5_prefix / "include")
                lib = str(hdf5_prefix / "lib")
                if inc not in include_dirs:
                    include_dirs.append(inc)
                    library_dirs.append(lib)
                extra_link_args.append(f"-Wl,-rpath,{lib}")
                break

        # Conda on macOS
        conda_inc = Path(sys.prefix) / "include"
        if _has_hdf5_header(conda_inc) and str(conda_inc) not in include_dirs:
            lib = str(Path(sys.prefix) / "lib")
            include_dirs.append(str(conda_inc))
            library_dirs.append(lib)
            extra_link_args.append(f"-Wl,-rpath,{lib}")

    # Validate and warn early if headers still not found
    if not any(_has_hdf5_header(Path(d)) for d in include_dirs):
        warnings.warn(
            "\n\n"
            "  *** Could not locate hdf5.h — build will likely fail. ***\n\n"
            "  Install HDF5 development headers:\n"
            "    Ubuntu/Debian : sudo apt install libhdf5-dev\n"
            "    Fedora/RHEL   : sudo dnf install hdf5-devel\n"
            "    macOS         : brew install hdf5\n"
            "    Conda         : conda install hdf5\n"
            "    Windows       : conda install hdf5  OR  vcpkg install hdf5\n\n"
            "  Or set HDF5_DIR to the HDF5 installation root and retry:\n"
            "    HDF5_DIR=/path/to/hdf5 pip install .\n",
            stacklevel=2,
        )

    return include_dirs, library_dirs, libraries, define_macros, extra_link_args


def get_compile_args() -> list[str]:
    if sys.platform == "win32":
        return [
            "/utf-8",   # treat source as UTF-8
            "/EHsc",    # standard C++ exception handling
            "/bigobj",  # allow large object files
            "/O2",      # optimise for speed
        ]
    # GCC / Clang (Linux + macOS)
    return [
        "-O2",
        "-fvisibility=hidden",  # only export pybind11 entry points
    ]


# ---------------------------------------------------------------------------
# Extension module
# ---------------------------------------------------------------------------

hdf5_inc, hdf5_lib, hdf5_libs, macros, link_args = find_hdf5()

ext_modules = [
    Pybind11Extension(
        "cffview.mesh_reader",
        sources=[
            "src/cffview/main.cxx",
            "src/cffview/vtkFLUENTCFFReader.cxx",
        ],
        include_dirs=[
            *hdf5_inc,
            str(Path("include")),
            np.get_include(),
            pybind11.get_include(),
        ],
        library_dirs=[*hdf5_lib, str(Path("lib"))],
        libraries=hdf5_libs,
        define_macros=macros,
        extra_compile_args=get_compile_args(),
        extra_link_args=link_args,
        cxx_std=17,
    ),
]

setup(
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
