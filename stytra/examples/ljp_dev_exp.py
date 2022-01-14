from stytra import Stytra, Protocol
from stytra.stimulation.stimuli.visual import Pause, FullFieldVisualStimulus, SeamlessImageStimulus, InterpolatedStimulus
from stytra.stimulation.stimuli import MovingGratingStimulus
from lightparam import Param

from stytra.triggering.socketTrigger import SocketTrigger


import pandas as pd
import numpy as np


class TestProtocol(Protocol):
    name = "test_protocol"

    stytra_config = dict(
        camera=dict(type="doublespinnaker"),
        tracking=dict(embedded=True, method="tail"),
    )
    
    def __init__(self):
        super().__init__()
        # Here we define these attributes as Param s. This will automatically
        #  build a control for them and make them modifiable live from the
        # interface.
        self.wait_duration = Param(10.0, limits=(0.2, None))
        self.flash_duration = Param(1.0, limits=(0.0, None))
        self.t_pre = Param(5.0)  # time of still gratings before they move
        self.t_move = Param(5.0)  # time of gratings movement
        self.grating_vel = Param(-10.0)  # gratings velocity
        self.grating_period = Param(10)  # grating spatial period
        self.grating_angle_deg = Param(90.0)  # grating orientation
    
    def get_stim_sequence(self):
        t = [0,self.t_pre,self.t_pre,self.t_pre + self.t_move,self.t_pre + self.t_move,2 * self.t_pre + self.t_move]
        vel = [0, 0, self.grating_vel, self.grating_vel, 0, 0]
        df = pd.DataFrame(dict(t=t, vel_x=vel))
            
        stimuli = [
            Pause(duration=self.wait_duration),
            FullFieldVisualStimulus(duration=self.flash_duration, color=(255, 255, 255)),
            MovingGratingStimulus(
                df_param=df,
                grating_angle=self.grating_angle_deg * np.pi / 180,
                grating_period=self.grating_period,
            )
        ]
        return stimuli
    
class FlashProtocol(Protocol):
    name = "flash_protocol"

    def get_stim_sequence(self):
        stimuli = [
            Pause(duration=4.0),
            FullFieldVisualStimulus(duration=1.0, color=(255, 255, 255)),
        ]
        return stimuli

class TestStimulations(Protocol):
    name = "test_protocol"

    def __init__(self):
        super().__init__()
        # Here we define these attributes as Param s. This will automatically
        #  build a control for them and make them modifiable live from the
        # interface.
        self.wait_duration = Param(10.0, limits=(0.2, None))
        self.flash_duration = Param(1.0, limits=(0.0, None))
        self.t_pre = Param(5.0)  # time of still gratings before they move
        self.t_move = Param(5.0)  # time of gratings movement
        self.grating_vel = Param(-10.0)  # gratings velocity
        self.grating_period = Param(10)  # grating spatial period
        self.grating_angle_deg = Param(90.0)  # grating orientation
        self.caustic_duration = Param(10.0, limits=(1, None))

    def get_stim_sequence(self):
        t = [0,self.t_pre,self.t_pre,self.t_pre + self.t_move,self.t_pre + self.t_move,2 * self.t_pre + self.t_move]
        vel = [0, 0, self.grating_vel, self.grating_vel, 0, 0]
        df = pd.DataFrame(dict(t=t, vel_x=vel))

        SeamInterp = type("stim", (SeamlessImageStimulus, InterpolatedStimulus), {})
            
        stimuli = [
            Pause(
                duration=self.wait_duration
            ),
            FullFieldVisualStimulus(
                duration=self.flash_duration, 
                color=(255, 255, 255)
            ),
            MovingGratingStimulus(
                df_param=df,
                grating_angle=self.grating_angle_deg * np.pi / 180,
                grating_period=self.grating_period,
            ),
            SeamInterp(
                background="/home/ljp/Documents/Images/caustic_semless1.jpg",
                df_param=pd.DataFrame(dict(t=[0, self.caustic_duration], vel_x=[10, 10], vel_y=[5, 5])),
            ),
        ]
        return stimuli


if __name__ == "__main__":
    
    #trigger = SocketTrigger(port='auto')
    #s = Stytra(protocol=FlashProtocol(), scope_triggering=trigger)
    
    s = Stytra(protocol=TestProtocol())

    #s = Stytra(protocol=TestStimulations())
















