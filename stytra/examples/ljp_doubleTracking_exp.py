from stytra import Stytra, Protocol

from stytra.stimulation.stimuli import Stimulus
from stytra.tracking.pipelines import Pipeline

from stytra.tracking.preprocessing import Prefilter, posdif
from stytra.tracking.tail import CentroidTrackingMethod
from stytra.tracking.eyes_luminance import EyeLumTrackingMethod
from stytra.gui.camera_display import TailTrackingSelection, EyeLumTrackingSelection

from stytra.tracking.pipelines import ImageToImageNode, NodeOutput
import numpy as np
from lightparam import Param


class RollingBackgroundSubtractor(ImageToImageNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="rollbgsub", **kwargs)
        self.diagnostic_image_options = ["rmv_BKGD", "BKGD"]
        self.background_image = None
        self.temp = None  # temporary image
        self.ntemp = 0  # number of images in current rolling mean
        self.change_flag = False  # wether the background has been changed
        self.lastMean = 0
        self.lastBackground_image = None

    def reset(self):
        self.background_image = None
    
    def changed(self, vals):
        if self.background_image is not None:
            mean = np.mean(self.background_image)
            if mean != self.lastMean:
                try:
                    self.background_image = np.load('BKGD.npy')
                except FileNotFoundError:
                    self.background_image = None
    
    def new_bkgd(self, im):
        self.background_image = im
        self.lastMean = np.mean(self.background_image)
        np.save("BKGD.npy", self.background_image)
        
    def _process(
        self,
        im,
        compute_background : Param(False),
    ):
        messages = []
        
        if self.background_image is None:
            self.new_bkgd(im)
            messages.append("I:New background image set")
        
        if compute_background:
            messages.append("I:Computing new background image")
            self.change_flag = True
            if self.temp is None:
                self.temp = im.astype(np.float32)
            else:
                self.temp += im.astype(np.float32)
            self.ntemp += 1
        else:
            if self.change_flag:
                self.new_bkgd((self.temp / self.ntemp).astype(np.float32))
                messages.append(f"I:New background image set from {self.ntemp} images")
                self.change_flag = False
                self.temp = None
                self.ntemp = 0
        
        
        out = posdif(self.background_image, im)
        if self.set_diagnostic == "rmv_BKGD":
            self.diagnostic_image = out
        if self.set_diagnostic == "BKGD":
            self.diagnostic_image = self.background_image
        
        return NodeOutput(messages, out )




class DoubleTrackingSelection(EyeLumTrackingSelection, TailTrackingSelection):
    pass

class DoubleTrackingPipeline(Pipeline):
    def __init__(self):
        super().__init__()
        self.eyetrack = EyeLumTrackingMethod(parent=self.root)

        self.bgsub = RollingBackgroundSubtractor(parent=self.root)
        self.filter = Prefilter(parent=self.bgsub)
        self.tailtrack = CentroidTrackingMethod(parent=self.filter)

        self.display_overlay = DoubleTrackingSelection


class EmptyProtocol(Protocol):
    name = "waits"

    def get_stim_sequence(self):
        return [Stimulus(duration=5.0)]


class DoubleEyesTailTrackerProtocol(EmptyProtocol):
    name = "DoubleTracker"

    stytra_config = dict(
        tracking=dict(
            embedded=True,
            method=DoubleTrackingPipeline,
        ),
        camera=dict(
            #video_file="/home/ljp/Run_03/14h37m02s.avi",
            type="doublespinnaker",
        ),
    )


if __name__ == "__main__":
    s = Stytra(protocol=DoubleEyesTailTrackerProtocol())













