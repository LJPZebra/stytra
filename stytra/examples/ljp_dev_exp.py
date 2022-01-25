from stytra import Stytra, Protocol
from stytra.stimulation.stimuli.visual import Pause, FullFieldVisualStimulus, SeamlessImageStimulus, InterpolatedStimulus
from stytra.stimulation.stimuli import MovingGratingStimulus
from lightparam import Param

from stytra.triggering.socketTrigger import SocketTrigger

from stytra.experiments.fish_pipelines import TailTrackingPipeline

from stytra.tracking.pipelines import Pipeline
from stytra.tracking.preprocessing import Prefilter, BackgroundSubtractor, negdif, absdif, posdif
from stytra.gui.camera_display import TailTrackingSelection
from stytra.tracking.tail import CentroidTrackingMethod
from stytra.gui.fishplots import TailStreamPlot
from stytra.tracking.pipelines import ImageToImageNode, NodeOutput


import pandas as pd
import numpy as np

import logging
logging.basicConfig(filename='main.log', level=logging.INFO)


class NewRollingBackgroundSubtractor(ImageToImageNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="rollbgsub", **kwargs)
        logging.info("[NRBS] init")
        self.diagnostic_image_options = ["rmv_BKGD", "BKGD"]
        self.background_image = None
        self.temp = None  # temporary image
        self.ntemp = 0  # number of images in current rolling mean
        self.change_flag = False  # wether the background has been changed
        self.lastMean = 0
        self.lastBackground_image = None

    def reset(self):
        logging.info("[NRBS] reset")
        self.background_image = None
    
    def changed(self, vals):
        #self.background_image = np.load('BKGD.npy')
        if self.background_image is not None:
            mean = np.mean(self.background_image)
            if mean != self.lastMean:
                logging.info(f"[NRBS] random change. setting back to previously saved background.")
                self.background_image = np.load('BKGD.npy')
    
    def new_bkgd(self, im):
        logging.info("[NRBS] getting and saving new bkgd")
        self.background_image = im
        self.lastMean = np.mean(self.background_image)
        np.save("BKGD.npy", self.background_image)
        
    def _process(
        self,
        im,
        compute_background : Param(False),
    ):
        messages = []
        logging.debug("[NRBS] process")
        
        if self.background_image is None:
            logging.info("[NRBS] is none")
            self.new_bkgd(im)
            messages.append("I:New background image set")
            #self.background_image = im
            #self.lastMean = np.mean(self.background_image)
            #np.save("BKGD.npy", self.background_image)
            #messages.append("I:New background image set")
        """
        if compute_background:
            logging.info("[NRBS] compyte bqckground")
            messages.append("I:Computing new background image")
            self.change_flag = True
            if self.temp is None:
                self.temp = im.astype(np.float32)
            else:
                self.temp += im.astype(np.float32)
            self.ntemp += 1
        else:
            if self.change_flag:
                logging.info("[NRBS] chqnge flqg")
                self.background_image[:, :] = (self.temp / self.ntemp).astype(np.float32)
                messages.append(f"I:New background image set from {self.ntemp} images")
                np.save("BKGD.npy", self.background_image)
                self.change_flag = False
                self.temp = None
                self.ntemp = 0
                self.lastSum = np.sum(self.background_image)
            elif np.sum(self.background_image) != self.lastSum:
                logging.info("[NRBS] background chqnge")
                messages.append(f"E:Bgd changed !!!!")
                #self.background_image = np.load("BKGD.npy")
                self.lastSum = np.sum(self.background_image)
        
        """
        out = posdif(self.background_image, im)
        if self.set_diagnostic == "rmv_BKGD":
            self.diagnostic_image = out
        if self.set_diagnostic == "BKGD":
            self.diagnostic_image = self.background_image
        
        return NodeOutput(messages, out )
        

class CustomTailPipeline(Pipeline):
    def __init__(self):
        super().__init__()
        self.bgsub = NewRollingBackgroundSubtractor(parent=self.root)
        #self.bgsub = BackgroundSubtractor(parent=self.root)
        self.filter = Prefilter(parent=self.bgsub)
        
        
        self.tailtrack = CentroidTrackingMethod(parent=self.filter)
        self.extra_widget = TailStreamPlot
        self.display_overlay = TailTrackingSelection


class TestTrackingProtocol(Protocol):
    name = "test_track_tracking"

    stytra_config = dict(
        tracking=dict(method=CustomTailPipeline),
        #camera=dict(video_file=str("/home/ljp/SSD/Data/2021-03-23/Run03/Images/tail_2021-03-23-174517-0003.avi")),
        camera=dict(type="doublespinnaker"),
    )

    def get_stim_sequence(self):
        # Empty protocol of specified duration:
        return [Pause(duration=10)]




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
            Pause(duration=2.0),
            FullFieldVisualStimulus(duration=2.0, color=(255, 255, 255)),
        ]
        return stimuli

class TestStimulations(Protocol):
    name = "test_stim_protocol"

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
    logging.info("[MAIN] ______________________________________________________")
    #trigger = SocketTrigger(port='auto')
    #s = Stytra(protocol=FlashProtocol(), scope_triggering=trigger)
    
    #s = Stytra(protocol=TestProtocol())

    #s = Stytra(protocol=TestStimulations())

    s = Stytra(protocol=TestTrackingProtocol())














