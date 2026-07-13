from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

ext_modules = [
    Pybind11Extension(
        "fv._core",
        ["src/fv/main.cpp"],
        include_dirs=["include"],
        library_dirs=["lib"],
        libraries=["hdf5"],
    ),
]

setup(
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
