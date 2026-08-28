"""HDF5 file introspection and raw Scheme export.

Reads metadata (version) from ``.h5`` case files and dumps the raw Scheme
text of ``/settings`` (Rampant / Thread / Cortex Variables) to ``*.scm``
files for inspection.
"""

import h5py


def print_version(file_path: str) -> None:
    """Get the version of the .h5 file

    Parameters
    ---------
    file_path : str
        Path to the .h5 file

    Returns
    -------
    str
        Version of the .h5 file
    """

    with h5py.File(file_path) as f:
        print(f['/settings/Version'][0].decode())


def extract_h5(file_path: str) -> None:
    """Extract cas.h5 general, boundary and cortex strings to files

    Parameters
    ---------
    file_path : str
        Path to the .h5 file
    """

    with h5py.File(file_path) as f:
        settings: h5py.Group = f['/settings']
        general_info = settings['Rampant Variables'][0].decode()
        boundary_info = settings['Thread Variables'][0].decode()
        cortex_info = settings['Cortex Variables'][0].decode()
    with open('general.scm', 'w', encoding='utf-8') as f:
        f.write(general_info)
    with open('boundary.scm', 'w', encoding='utf-8') as f:
        f.write(boundary_info)
    with open('cortex.scm', 'w', encoding='utf-8') as f:
        f.write(cortex_info)
