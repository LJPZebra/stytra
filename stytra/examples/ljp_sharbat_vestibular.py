# Sharbat 2022
# Vestibular experiment (either use this in itself or with LabView motor)
# Note that the communication is still via Matlab as Soloist (Aerotech) has MATLAB API only

from stytra import Stytra, Protocol

from stytra.stimulation.stimuli import Stimulus
from stytra.stimulation.stimuli.ljp_vestibular import VestibularStimulus
from stytra.tracking.pipelines import Pipeline

from stytra.tracking.preprocessing import Prefilter, posdif
from stytra.tracking.tail import CentroidTrackingMethod
#from stytra.tracking.eyes_luminance import EyeLumTrackingMethod
from stytra.gui.camera_display import TailTrackingSelection

from stytra.tracking.pipelines import ImageToImageNode, NodeOutput
import numpy as np
import pandas as pd
from lightparam import Param 

from stytra.examples.ljp_doubleTracking_exp import RollingBackgroundSubtractor

import logging
logging.basicConfig(filename='main.log', level=logging.INFO)

class TrackingPipeline(Pipeline):
    def __init__(self):
        super().__init__()
        
        self.bgsub = RollingBackgroundSubtractor(parent=self.root)
        self.filter = Prefilter(parent=self.bgsub)
        self.tailtrack = CentroidTrackingMethod(parent=self.filter)

        self.display_overlay = TailTrackingSelection


class EmptyProtocol(Protocol):
    name = "waits"

    def get_stim_sequence(self):
        return [NewVestibularStimulus(duration=self.exp_duration)]


class VestibularTailTrackerProtocol(EmptyProtocol):
    name = "VestibularTailTracker"

    stytra_config = dict(
        tracking=dict(
            embedded=True,
            method=TrackingPipeline,
        ),
        camera=dict(
            #video_file="/home/ljp/Run_03/14h37m02s.avi",
            type="doublespinnaker",
        ),
    )


    
if __name__ == "__main__":
    s = Stytra(protocol=VestibularTailTrackerProtocol())

