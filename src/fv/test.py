import pyvista as pv
import os
import sys

dll_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../lib"))

# 🌟 核心：在 Windows 且 Python 3.8+ 环境下，必须这样注册 DLL 目录
if sys.platform == "win32" and os.path.exists(dll_dir):
    os.add_dll_directory(dll_dir)
    from fv import mesh_reader

# file_path_msh = "square-10x10-quad.msh.h5"
# file_path_cas = "square-10x10-quad.cas.h5"

file_path_msh = "test.msh.h5"
file_path_cas = "test.cas.h5"

# ret_msh = mesh_reader.read_mesh_data(file_path_msh)
# print(ret_msh['cells'][:10])
# ret_cas = mesh_reader.read_mesh_data(file_path_cas)
# print(ret_cas['cells'][:10])

ret2 = mesh_reader.read_pyvista_mesh(file_path_cas)
print(ret2)

pv.plot(
    ret2,
    show_edges=True,
    show_axes=True,
    smooth_shading=True,
    split_sharp_edges=True,
)
