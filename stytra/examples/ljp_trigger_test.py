import numpy as np
import pandas as pd

from stytra import Stytra
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli.visual import Pause
from stytra.stimulation.stimuli import MovingGratingStimulus
from lightparam import Param
from pathlib import Path

from stytra.stimulation.stimuli import VisualStimulus
from PyQt5.QtCore import QPoint, QRect, QPointF, Qt
from PyQt5.QtGui import QPainter, QBrush, QColor, QPen, QTransform, QPolygon, QRegion
import time
from math import cos, pi
from stytra.triggering.socketTrigger import SocketTrigger

class TimeStimulus(VisualStimulus):
    def __init__(self, period=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.startT = time.time()
        self.period = period
        
    def paint(self,p,w,h):
        t = (time.time() - self.startT)
        lum = int((cos(2*pi*t/self.period)+1)/2*255)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(lum,lum,lum)))  # Use chosen color
        self.clip(p, w, h)
        p.drawRect(QRect(-1, -1, w + 2, h + 2))  # draw full field rectangle

class TestProtocol(Protocol):
    name = "trigger_test"
    
    def get_stim_sequence(self):
        return [TimeStimulus(duration=10)]


class GratingsProtocol(Protocol):
    name = "gratings_protocol"

    def __init__(self):
        super().__init__()

        self.t_pre = Param(5.0)  # time of still gratings before they move
        self.t_move = Param(5.0)  # time of gratings movement
        self.grating_vel = Param(-10.0)  # gratings velocity
        self.grating_period = Param(10)  # grating spatial period
        self.grating_angle_deg = Param(90.0)  # grating orientation

    def get_stim_sequence(self):
        # Use six points to specify the velocity step to be interpolated:
        t = [
            0,
            self.t_pre,
            self.t_pre,
            self.t_pre + self.t_move,
            self.t_pre + self.t_move,
            2 * self.t_pre + self.t_move,
        ]

        vel = [0, 0, self.grating_vel, self.grating_vel, 0, 0]

        df = pd.DataFrame(dict(t=t, vel_x=vel))

        return [
            MovingGratingStimulus(
                df_param=df,
                grating_angle=self.grating_angle_deg * np.pi / 180,
                grating_period=self.grating_period,
            )
        ]


if __name__ == "__main__":
    # We make a new instance of Stytra with this protocol as the only option
    trigger = SocketTrigger(port='auto')
    s = Stytra(protocol=TestProtocol(), scope_triggering=trigger)
