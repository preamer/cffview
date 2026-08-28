"""Plot Ansys Fluent export data files with matplotlib.

Supports Fluent's ``.out`` report files, ``.xy`` plot exports and the
residuals stored inside ``.dat.h5`` files.
"""


def plot(file_path: str, out: bool = False, xy: bool = False, dat: bool = False) -> None:
    """Plot Ansys Fluent export data files

    Parameters
    ---------
    file_path : str
        Path to the data file
    out : bool
        If True, plot .out data file
    xy : bool
        If True, plot .xy data file
    dat : bool
        If True, plot .dat.h5 residuals data
    """
    import re
    import numpy as np
    import matplotlib.pyplot as plt

    pattern = re.compile(r'"([^"]*)"')

    def plot_out(file_path: str) -> None:
        with open(file_path, encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                match line_num:
                    case 1:
                        title = re.findall(pattern, line)[0]
                    case 2:
                        _, *report_definitions = re.findall(pattern, line)
                    case 3:
                        xlabel, *ylabels = re.findall(pattern, line)
                    case _:
                        break

        data = np.loadtxt(file_path, skiprows=3)
        plt.figure()
        plt.plot(data[:, 0], data[:, 1:])
        plt.title(title)
        plt.xlabel(xlabel)
        plt.legend(ylabels)
        plt.grid()
        plt.show()

    def plot_xy(file_path: str) -> None:
        with open(file_path, encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                match line_num:
                    case 1:
                        title = re.findall(pattern, line)[0]
                    case 2:
                        x_axis_title, y_axis_title = re.findall(pattern, line)
                    case _:
                        content = f.read()
                        break
        chunks = content.split('((xy/key/label "')[1:]
        data = {}
        for chunk in chunks:
            label, rest = chunk.split('"', 1)
            first_bracket = rest.find(")")
            last_bracket = rest.rfind(")")
            data_str = rest[first_bracket + 1: last_bracket]
            arr_2d = np.fromstring(data_str, dtype=np.float64, sep=" ").reshape(-1, 2)
            data[label] = arr_2d[arr_2d[:, 0].argsort()]

        plt.figure()
        for label, arr_2d in data.items():
            plt.plot(arr_2d[:, 0], arr_2d[:, 1], label=label)
        plt.title(title)
        plt.xlabel(x_axis_title)
        plt.ylabel(y_axis_title)
        plt.legend()
        plt.grid()
        plt.show()

    def plot_dat(file_path: str) -> None:
        from h5py import File, Group

        data = {}

        with File(file_path) as f:
            residuals: Group = f['/results/residuals']
            for phase_name, phase_group in residuals.items():
                data[phase_name] = {}
                for eq_name, eq_group in phase_group.items():
                    data[phase_name][eq_name] = {
                        'data': eq_group['data'][:, 0] / eq_group['data'][:, 1],
                        'iterations': eq_group['iterations'][:]
                    }
        phase_num = len(data)

        plt.figure()
        for i, (phase_name, phase_dict) in enumerate(data.items(), start=1):
            plt.subplot(1, phase_num, i)
            for eq_name, eq_dict in phase_dict.items():
                plt.plot(eq_dict['iterations'], eq_dict['data'], label=eq_name)
            plt.xlabel('iterations')
            plt.ylabel('residuals')
            plt.yscale('log')
            plt.title(phase_name)
            plt.legend()
            plt.grid()
        plt.show()

    if out:
        plot_out(file_path)
    elif xy:
        plot_xy(file_path)
    elif dat:
        plot_dat(file_path)
    else:
        file_ext = file_path.split('.')[-1]
        if file_ext == 'out':
            plot_out(file_path)
        elif file_ext == 'xy':
            plot_xy(file_path)
        elif file_path.endswith('.dat.h5'):
            plot_dat(file_path)
