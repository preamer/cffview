"""Interactive PyVista visualisation of Fluent meshes and data.

:class:`MeshPlotter` shows the geometry of a ``.cas.h5`` / ``.msh.h5`` file,
while :class:`DataPlotter` visualises cell data from a ``.dat.h5`` file with
variable switching, opacity and clip-plane widgets.
"""

import sys
from functools import wraps

from pyvista import _vtk, Actor, Plotter, MultiBlock, PolyData, UnstructuredGrid, DataSetMapper

from .utils import print_colored_dict

# PyVista plotter's default keyboard shortcuts
KEYBOARD_SHORTCUTS = {
    'q': 'Close the rendering window',
    'f': 'Focus and zoom in on a point',
    'v': 'Isometric camera view',
    'w': 'Switch all datasets to a wireframe representation',
    'r': 'Reset the camera to view all datasets',
    's': 'Switch all datasets to a surface representation',
    'shift+click or middle-click' if not sys.platform.startswith('darwin') else 'shift+click': 'Pan the rendering scene',
    'left-click' if not sys.platform.startswith('darwin') else 'cmd+click': 'Rotate the rendering scene in 3D',
    'ctrl+click': 'Rotate the rendering scene in 2D(view-plane)',
    'mouse-wheel or right-click' if not sys.platform.startswith('darwin') else 'ctl+click': 'Continuously zoom the rendering scene',
    'shift+s': 'Save a screenshot(only on BackgroundPlotter)',
    'shift+c': 'Enable interactive cell selection/picking',
    'up/down': 'Zoom in and out',
    '+ /-': 'Increase/decrease the point size and line widths',
}


class BasePlotter:
    def __init__(self, mesh: MultiBlock | PolyData) -> None:
        self.mesh = mesh.combine() if isinstance(mesh, MultiBlock) else mesh
        self.dimension = 2 if all(self.mesh.points[:, 2] == 0.0) else 3

        # Monkey patch to fix clip plane error
        if isinstance(self.mesh, UnstructuredGrid):
            _vtk._CORE_MODULES['vtkFiltersGeneral'] = (
                *_vtk._CORE_MODULES['vtkFiltersGeneral'], 'vtkClipDataSet'
            )
            _vtk._VTK_CLASS_TO_MODULE = {
                cls: module
                for module, classes in (
                    _vtk._CORE_MODULES | _vtk._PLOTTING_MODULES | _vtk._OPENGL_MODULES
                ).items()
                for cls in classes
            }
            _vtk.vtkTableBasedClipDataSet = _vtk.vtkClipDataSet

        self.pl = Plotter()
        self.pl.enable_anti_aliasing()
        self.pl.add_axes(viewport=(0.8, 0.0, 1.0, 0.2))
        self.keyboard_shortcuts = KEYBOARD_SHORTCUTS

    @wraps(Plotter.show)
    def show(self, *args, **kwargs) -> None:
        print_colored_dict(self.keyboard_shortcuts)
        self.pl.show(*args, **kwargs)

    def _add_checkbox_and_text(
            self,
            checkbox_params: dict = None,
            text_params: dict = None,
    ) -> _vtk.vtkButtonWidget:
        checkbox_params = checkbox_params or {}
        text_params = text_params or {}

        if not text_params.get('position') and checkbox_params.get('position'):
            text_params['position'] = (
                checkbox_params['position'][0] + 50,
                checkbox_params['position'][1] + 10,
            )

        check_box_widget: _vtk.vtkButtonWidget = self.pl.add_checkbox_button_widget(**checkbox_params)
        check_box_widget.callback = checkbox_params['callback']
        self.pl.add_text(**text_params)

        return check_box_widget

    def _add_grid_cb(self) -> _vtk.vtkButtonWidget:
        def toggle_grid(state: bool) -> None:
            self.pl.show_grid(font_size=10, fmt='%.2f') if state else self.pl.remove_bounds_axes()

        grid_cb: _vtk.vtkButtonWidget = self._add_checkbox_and_text(
            checkbox_params=dict(
                callback=toggle_grid,
                value=False,
                position=(10, 55),
                size=40,
            ),
            text_params=dict(
                text='Show Grid',
                font_size=10,
            )
        )
        return grid_cb

    def _add_keyboard_shortcuts(self, key_widget_dict: dict[str, tuple[_vtk.vtkButtonWidget | _vtk.vtkSliderWidget, str]]):
        def reverse(checkbox_button_widget: _vtk.vtkButtonWidget) -> None:
            rep = checkbox_button_widget.button_representation
            new_state = not rep.state
            rep.state = new_state
            checkbox_button_widget.callback(new_state)

        def set_value(slider_widget: _vtk.vtkSliderWidget, new_value: int) -> None:
            slider_widget.slider_representation.value = new_value
            slider_widget.callback(new_value)

        for key, (widget, help_info) in key_widget_dict.items():
            if isinstance(widget, _vtk.vtkButtonWidget):
                self.pl.add_key_event(key, lambda w=widget: reverse(w))
            elif isinstance(widget, _vtk.vtkSliderWidget):
                self.pl.add_key_event(key, lambda w=widget, v=int(key): set_value(w, v))
            self.keyboard_shortcuts[key] = help_info


class MeshPlotter(BasePlotter):
    def __init__(self, mesh, dimension: int, mesh_info: dict[str, int]) -> None:
        super().__init__(mesh)
        self.dimension = dimension
        self.mesh_info = mesh_info
        self._add_mesh_info()
        self.mesh_actor = self._add_mesh()
        self.opacity_slider_widget = self._add_opcatity_slider()
        self._add_mesh_clip_plane()
        self.clip_plane_cb = self._add_clip_plane_cb()
        self.grid_cb = self._add_grid_cb()
        self._add_keyboard_shortcuts(
            {
                'c': (self.clip_plane_cb, 'Clip Plane'),
                'g': (self.grid_cb, 'Toggle Grid')
            }
        )

    def _add_mesh_info(self) -> None:
        self.pl.add_text(
            text=f'Nodes: {self.mesh_info["n_nodes"]}\n'
            f'Faces: {self.mesh_info["n_faces"]}\n'
            f'Cells: {self.mesh_info["n_cells"]}',
            font_size=10,
        )

    def _add_mesh(self) -> Actor:
        mesh_actor = self.pl.add_mesh(
            self.mesh,
            show_edges=True,
            line_width=5 if self.dimension == 2 else None,
        )
        return mesh_actor

    def _add_opcatity_slider(self) -> _vtk.vtkSliderWidget:
        opacity_slider_widget: _vtk.vtkSliderWidget = self.pl.add_slider_widget(
            lambda value: setattr(self.mesh_actor.prop, 'opacity', value),
            rng=(0.1, 1.0),
            value=1.0,
            title="Opacity",
            style="modern",
            pointa=(0.55, 0.93),
            pointb=(0.95, 0.93),
            slider_width=0.03,
            tube_width=0.03,
            title_height=0.03,
        )
        return opacity_slider_widget

    def _add_mesh_clip_plane(self) -> None:
        self.mesh_clip_plane_actor = self.pl.add_mesh_clip_plane(self.mesh, show_edges=True)
        self.mesh_clip_plane_actor.visibility = False
        self.clip_plane = self.pl.widgets.plane_widgets[-1]
        self.clip_plane.Off()

    def _add_clip_plane_cb(self) -> _vtk.vtkButtonWidget:
        def toggle_clip_plane(state) -> None:
            if state:
                self.mesh_actor.visibility = False
                self.opacity_slider_widget.Off()
                self.mesh_clip_plane_actor.visibility = True
                self.clip_plane.On()
            else:
                self.mesh_actor.visibility = True
                self.opacity_slider_widget.On()
                self.mesh_clip_plane_actor.visibility = False
                self.clip_plane.Off()

        clip_plane_cb = self._add_checkbox_and_text(
            checkbox_params=dict(
                callback=toggle_clip_plane,
                value=False,
                position=(10, 10),
                size=40,
            ),
            text_params=dict(
                text='Clip Plane',
                font_size=10,
            )
        )
        return clip_plane_cb


class DataPlotter(BasePlotter):
    def __init__(self, mesh: MultiBlock | PolyData) -> None:
        super().__init__(mesh)
        self.var_names = [
            'SV_P',
            'SV_T',
            'SV_DENSITY',
            'SV_U', 'SV_V', 'SV_W',
            'SV_H',
        ]
        self.var_names.remove('SV_W') if self.dimension == 2 else None
        print(f"{len(self.var_names)} variable(s) available:")
        for i, name in enumerate(self.var_names):
            print(f"    [{i}] {name}")

        self.scalar_ranges = {
            name: self.mesh.get_data_range(name, preference=self._scalar_mode(name))
            for name in self.var_names
        }

        self.mesh_actor = self.pl.add_mesh(
            self.mesh,
            name='mesh',
            cmap='turbo',
            scalars=self.var_names[0],
            scalar_bar_args={
                'title': self.var_names[0],
                'vertical': True,
                'position_x': 0.85,
                'position_y': 0.2,
                'height': 0.7,
                'width': 0.1,
            },
        )
        self.scalar_bar: _vtk.vtkScalarBarActor = next(iter(self.pl.scalar_bars.values()))

        self.mesh_clip_plane_actor = self.pl.add_mesh_clip_plane(
            self.mesh,
            name='clip_mesh',
            cmap='turbo',
            scalars=self.var_names[0],
            show_scalar_bar=False,
        )
        self.mesh_clip_plane_actor.visibility = False
        self.clip_plane = self.pl.widgets.plane_widgets[-1]
        self.clip_plane.Off()

        self.clip_plane_cb = self._add_clip_plane_cb()
        self.scalar_slider = self._add_scalar_slider_widget()
        self.grid_cb = self._add_grid_cb()
        self._add_keyboard_shortcuts(
            {
                'c': (self.clip_plane_cb, 'Clip Plane'),
                'g': (self.grid_cb, 'Toggle Grid'),
                **{
                    str(index): (self.scalar_slider, f'Show {self.var_names[index]}')
                    for index in range(len(self.var_names))
                },
            }
        )

    def _scalar_mode(self, name: str) -> str:
        return 'cell' if name in self.mesh.cell_data else 'point'

    def _set_scalars(self, name: str) -> None:
        """Switch the displayed variable without rebuilding any actor."""
        mode = self._scalar_mode(name)
        for actor in (self.mesh_actor, self.mesh_clip_plane_actor):
            mapper: DataSetMapper = actor.mapper
            mapper.scalar_map_mode = mode
            mapper.set_active_scalars(name, preference=mode)
            mapper.scalar_range = self.scalar_ranges[name]
        self.scalar_bar.title = name
        self.pl.render()

    def _add_scalar_slider_widget(self) -> _vtk.vtkSliderWidget:
        def change_scalar(value: float) -> None:
            self._set_scalars(self.var_names[int(value)])

        scalar_slider: _vtk.vtkSliderWidget = self.pl.add_slider_widget(
            change_scalar,
            rng=(0, len(self.var_names) - 1),
            value=0,
            title="Scalar Index",
            style="modern",
            pointa=(0.05, 0.93),
            pointb=(0.45, 0.93),
            slider_width=0.03,
            tube_width=0.03,
            title_height=0.03,
            fmt='%.0f',
        )
        scalar_slider.callback = change_scalar
        return scalar_slider

    def _add_clip_plane_cb(self) -> _vtk.vtkButtonWidget:
        def toggle_clip_plane(state) -> None:
            if state:
                self.mesh_actor.visibility = False
                self.mesh_clip_plane_actor.visibility = True
                self.clip_plane.On()
            else:
                self.mesh_actor.visibility = True
                self.mesh_clip_plane_actor.visibility = False
                self.clip_plane.Off()

        clip_plane_cb = self._add_checkbox_and_text(
            checkbox_params=dict(
                callback=toggle_clip_plane,
                value=False,
                position=(10, 10),
                size=40,
            ),
            text_params=dict(
                text='Clip Plane',
                font_size=10,
            )
        )
        return clip_plane_cb
