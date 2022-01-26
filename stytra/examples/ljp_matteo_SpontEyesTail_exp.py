from stytra import Stytra
from stytra.stimulation.stimuli import Stimulus
from stytra.triggering.socketTrigger import SocketTrigger
from lightparam import Param

from stytra.examples.ljp_doubleTracking_exp import DoubleEyesTailTrackerProtocol



class SpontaneousEyesTailProtocol(DoubleEyesTailTrackerProtocol):
    name = "spontaneousEyesTail"

    def __init__(self):
        super().__init__()
        self.exp_duration = Param(1500., limits=(10., 15000.))

    def get_stim_sequence(self):
        return [Stimulus(duration=self.exp_duration)]




if __name__ == "__main__":
    trigger = SocketTrigger(port='auto')
    s = Stytra(protocol=SpontaneousEyesTailProtocol(), scope_triggering=trigger)
