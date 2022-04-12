from stytra import Stytra
from stytra.stimulation.stimuli import Stimulus
from stytra.triggering.socketTrigger import SocketTrigger
from lightparam import Param

from stytra.examples.ljp_doubleTracking_exp import DoubleEyesTailTrackerProtocol

from itertools import product

import numpy as np
import pims
import qimage2ndarray
from pathlib import Path

from PyQt5.QtCore import QPoint, QRect, QPointF, Qt
from PyQt5.QtGui import QPainter, QBrush, QColor, QPen, QTransform, QPolygon, QRegion

from stytra.stimulation.stimuli import (
    Stimulus,
    DynamicStimulus,
    InterpolatedStimulus,
    CombinerStimulus,
)

import matlab.engine

eng = matlab.engine.start_matlab();

motor = eng.Soloist(); # a matlab handle object

# usage : Soloist class defines get and set methods for properties, we can access properties without 
# using the MATLAB workspace, use the following & always use

eng.home(motor, nargout = 0)

# move a certain angle
angle = 10 #degrees
eng.moveAbs(motor, angle, nargout=0)

# read current angle, need nargout=1 to read angle
current_angle = eng.readPos(motor, nargout = 1)
print(current_angle)

eng.home(motor, nargout = 0)

eng.quit()





