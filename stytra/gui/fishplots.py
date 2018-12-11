from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
import pyqtgraph as pg
import numpy as np
import datetime
from stytra.collectors import Accumulator
from stytra.collectors import QueueDataAccumulator
from stytra.tracking.online_bouts import find_bouts_online, BoutState
from stytra.utilities import reduce_to_pi

from collections import deque
from lightparam import Param, Parametrized
from lightparam.gui import ControlSpin

from scipy.ndimage.filters import gaussian_filter1d


class StreamingPositionPlot(pg.GraphicsWindow):
    """Plot that displays the virtual position of the fish"""

    def __init__(self, *args, data_accumulator, n_points=500, **kwargs):
        super().__init__(*args, **kwargs)
        assert isinstance(data_accumulator, Accumulator)
        self.positionPlot = self.addPlot()
        self.positionPlot.setAspectLocked(True)
        self.curve = self.positionPlot.plot()

        self.n_points = n_points
        self.start = datetime.datetime.now()
        self.data_accumulator = data_accumulator
        self.ind_x = self.data_accumulator.header_list.index("x")
        self.ind_y = self.data_accumulator.header_list.index("y")

    def update(self):
        """ """
        try:
            data_array = self.data_accumulator.get_last_n(self.n_points)
            velocity = np.r_[
                np.clip(
                    np.diff(data_array[:, self.ind_x]) ** 2
                    + np.diff(data_array[:, self.ind_y]) ** 2,
                    0,
                    30,
                )
                / 30,
                [0],
            ]
            self.curve.setData(
                x=data_array[:, self.ind_x],
                y=data_array[:, self.ind_y],
                color=np.stack(
                    [
                        0.5 + 0.5 * velocity,
                        0.2 + 0.8 * velocity,
                        velocity,
                        np.ones_like(velocity),
                    ],
                    1,
                ),
            )

        except (IndexError, TypeError):
            pass


class TailStreamPlot(QWidget):
    def __init__(self, acc, headers, n_points=300):
        super().__init__()
        self.acc = acc
        self.headers = headers
        self.n_points = n_points

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.display_widget = pg.GraphicsLayoutWidget()
        self.vb_display = pg.ViewBox()
        self.display_widget.addItem(self.vb_display)
        self.image_item = pg.ImageItem()
        self.vb_display.addItem(self.image_item)

        self.image_item.setLevels((-0.6, 0.6))
        self.image_item.setLookupTable(
            pg.ColorMap(
                np.linspace(0, 1, 5),
                np.array(
                    [
                        [0.42107294, 0.80737975, 0.49219722],
                        [0.23166242, 0.39962101, 0.32100403],
                        [0.0, 0.0, 0.0],
                        [0.46170494, 0.30327584, 0.38740225],
                        [0.91677407, 0.58427975, 0.92293321],
                    ]
                ),
            ).getLookupTable(alpha=False)
        )
        self.layout().addWidget(self.display_widget)

    def update(self):
        if not self.isVisible():
            return
        data_array = self.acc.get_last_n(self.n_points)
        if len(data_array) > 0:
            self.image_item.setImage(
                image=np.diff(data_array[:, 2:], axis=1).T, autoLevels=False
            )


def rot_mat(theta):
    """The rotation matrix for an angle theta """
    return np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])


def angle_mean(angles, axis=1):
    """Correct calculation of a mean of an array of angles"""
    return np.arctan2(np.sum(np.sin(angles)), np.sum(np.cos(angles)))


def normalise_bout(coord):
    """ Reset a bout to be facing upward and start from 0,0

    Parameters
    ----------
    bout

    Returns
    -------

    """
    dir_init = angle_mean(coord[:2, 2])
    coord[:, :2] = (coord[:, :2] - coord[:1, :2]) @ rot_mat(dir_init + np.pi)
    coord[:, 2] -= dir_init
    coord[:, 2] = reduce_to_pi(coord[:, 2])
    return coord


class BoutPlot(QWidget, Parametrized):
    def __init__(self, acc: QueueDataAccumulator, i_fish=0, n_bouts=10, n_save_max=300):
        super().__init__()
        self.acc = acc
        self.bouts = deque()
        self.i_fish = i_fish
        self.processed_index = 0
        self.velocity_threshold = Param(0.2)
        self.n_bouts = n_bouts
        self.old_coords = None
        self.i_curve = 0
        self.n_save_max = n_save_max

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(ControlSpin(self, "velocity_threshold"))

        self.vmax = 0
        self.lbl_vmax = QLabel()
        self.layout().addWidget(self.lbl_vmax)

        self.display_widget = pg.GraphicsLayoutWidget()
        self.layout().addWidget(self.display_widget)
        self.vb_display = pg.ViewBox()
        self.vb_display.setAspectLocked(True, 1)
        self.vb_display.setRange(xRange=[-1, 5], disableAutoRange=True)
        self.vb_display.invertY(True)
        self.display_widget.addItem(self.vb_display)

        self.bout_curves = [
            pg.PlotCurveItem(connect="finite") for _ in range(self.n_bouts)
        ]

        # temporary, remove
        # self.hline = pg.InfiniteLine(angle=0)
        # self.vb_display.addItem(self.hline)

        self.colors = np.zeros(self.n_bouts)
        self.decay_constant = 0.99

        self.bout_coords = None
        self.bout_state = BoutState(0, 0.0, 0, 0, 0)

        for c in self.bout_curves:
            self.vb_display.addItem(c)

    def update(self):
        if not self.isVisible():
            self.vmax = 0
            return

        current_index = len(self.acc.stored_data)
        if current_index == 0 or current_index < self.processed_index + 2:
            return

        # Pull the new data from the accumulator
        new_coords = np.array(
            self.acc.stored_data[
                max(
                    self.processed_index, current_index - self.n_save_max
                ) : current_index
            ]
        )
        self.processed_index = current_index

        ix, iy, ith = (
            self.acc.header_dict["f{:d}_{}".format(self.i_fish, var)]
            for var in ["x", "y", "theta"]
        )

        new_coords = new_coords[:, [ix, iy, ith]]

        # if in the previous refresh we ended up inside a bout, there are still
        # coordinates left to process
        if self.old_coords is not None:
            pre_start = len(self.old_coords)
            new_coords = np.concatenate([self.old_coords, new_coords], 0)
        else:
            pre_start = 0

        vel = np.sum(np.diff(new_coords[:, :2], axis=0) ** 2, axis=1)

        self.vmax = np.nanmax(vel)
        self.lbl_vmax.setText("max velocity sq {:.1f}".format(self.vmax))

        if self.bout_coords is None:
            self.bout_coords = [new_coords[0,:]]

        new_bout = None
        if self.velocity_threshold > 0:
            self.bout_coords, bout_finished, self.bout_state = find_bouts_online(
                vel,
                new_coords,
                self.bout_state,
                bout_coords=self.bout_coords,
                shift=pre_start,
                threshold=self.velocity_threshold,
                pad_after=5,
                pad_before=4,
                min_bout_len=5,
            )
            if bout_finished:
                new_bout = self.bout_coords
                self.bout_coords = [new_coords[0, :]]

        self.old_coords = new_coords[-self.n_save_max:, :]

        self.colors *= self.decay_constant

        if new_bout and len(new_bout)>2:
            nb = normalise_bout(np.array(new_bout[1:]))
            self.bout_curves[self.i_curve].setData(x=nb[:, 0], y=nb[:, 1])
            self.colors[self.i_curve] = 255
            self.i_curve = (self.i_curve + 1) % self.n_bouts

        for i_c, (curve, color) in enumerate(zip(self.bout_curves, self.colors)):
            col = int(color)
            if col < 10:
                curve.setData(x=[], y=[])
            else:
                curve.setPen((col, col, col))