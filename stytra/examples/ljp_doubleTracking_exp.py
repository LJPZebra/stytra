from stytra import Stytra, Protocol
from stytra.stimulation.stimuli import Stimulus
from stytra.tracking.pipelines import Pipeline
from stytra.tracking.preprocessing import Prefilter
from stytra.tracking.tail import CentroidTrackingMethod
from stytra.tracking.eyes_luminance import EyeLumTrackingMethod
from stytra.gui.camera_display import TailTrackingSelection, EyeLumTrackingSelection



class DoubleTrackingSelection(EyeLumTrackingSelection, TailTrackingSelection):
    pass

class DoubleTrackingPipeline(Pipeline):
    def __init__(self):
        super().__init__()
        self.eyetrack = EyeLumTrackingMethod(parent=self.root)

        self.filter = Prefilter(parent=self.root)
        self.tailtrack = CentroidTrackingMethod(parent=self.filter)

        self.display_overlay = DoubleTrackingSelection


class EmptyProtocol(Protocol):
    name = "waits"

    def get_stim_sequence(self):
        return [Stimulus(duration=5.0)]


class SimpleDoubleTrackerProtocol(EmptyProtocol):
    name = "simpleDoubleTracker"

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
    s = Stytra(protocol=SimpleDoubleTrackerProtocol())













