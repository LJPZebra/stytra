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

# eng = matlab.engine.start_matlab();

class VestibularStimulus(Stimulus):
    """Stimulus class to deliver vestibular stimulus
    We will deliver vestibular stimulus via Matlab engine (only Matlab 2020) on python
    because of the available API
    Parameters
    ----------
    
    default_speed
    
    Returns
    -------
    """

    def __init__(self, *args, **kwargs):
        """ """
        super().__init__(*args, **kwargs)
        self.default_speed = 15
        eng = matlab.engine.start_matlab()
        self.motor = eng.Soloist
        eng.home(self.motor, nargout = 0)
        

    """
    check Soloist.m for functions to be implemented
    SoloistMotionEnable(obj.handle)
    SoloistMotionHome(obj.handle)
    setSoftLimits ## to be implemented ##
    
    """
    def paint(self, p, w, h):
        """Paint function. Called by the StimulusDisplayWindow update method
        (NOT by the `ProtocolRunner.update()` !).
        Parameters
        ----------
        p : QPainter object
            Painter object for drawing
        w :
            width of the display window
        h :
            height of the display window
        Returns
        -------
        """
        pass

