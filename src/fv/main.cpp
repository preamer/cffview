#include <pybind11/pybind11.h>

namespace py = pybind11;

int add(int i, int j) {
    return i + j;
}

// 注意：这里的名字必须是 _core
PYBIND11_MODULE(_core, m) {
    m.doc() = "C++ core extension for fv";
    m.def("add", &add, "A function that adds two numbers");
}
