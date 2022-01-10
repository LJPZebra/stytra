from stytra import Stytra, Protocol
from stytra.stimulation.stimuli.visual import Pause, FullFieldVisualStimulus

from stytra.triggering.socketTrigger import SocketTrigger


class Nostim(Protocol):
    name = "empty_protocol"

    stytra_config = dict(camera=dict(type="doublespinnaker"))
    
    def get_stim_sequence(self):
        return [Pause(duration=10)]  # protocol does not do anything 
    
class FlashProtocol(Protocol):
    name = "flash_protocol"

    def get_stim_sequence(self):
        stimuli = [
            Pause(duration=4.0),
            FullFieldVisualStimulus(duration=1.0, color=(255, 255, 255)),
        ]
        return stimuli


if __name__ == "__main__":
    
    #trigger = SocketTrigger(port='auto')
    #s = Stytra(protocol=FlashProtocol(), scope_triggering=trigger)
    
    s = Stytra(protocol=Nostim())
