from stytra.experiments import Experiment
from stytra.experiments.tracking_experiments import (
    CameraExperiment,
    TrackingExperiment,
    SwimmingRecordingExperiment,
)
from stytra.calibration import CircleCalibrator
from stytra.utilities import recursive_update

# imports for easy experiment building
from stytra.metadata import AnimalMetadata, GeneralMetadata
from stytra.stimulation import Protocol

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

import pkg_resources
import qdarkstyle
import pyqtgraph as pg
import json

from pathlib import Path


class Stytra:
    """ Stytra application instance. Contains the QApplication and
    constructs the appropriate experiment object for the specified
    parameters

    Parameters
    ==========
        protocols : list(Protocol)
            the protocols to be made available from the dropdown

        display_config : dict
            full_screen : bool
                displays the stimulus full screen on the secondary monitor, otherwise
                it is in a window
            window_size : tuple(int, int)
                optional specification of the size of the stimulus display area

        camera_config : dict
            video_file : str
                or
            type: str
                supported cameras are
                "ximea" (with the official API)
                "avt" (With the Pymba API)
                "spinnaker" (PointGray/FLIR)

            rotation: int
                how many times to rotate the camera image by 90 degrees to get the
                right orientation, matching the projector

            downsampling: int
                how many times to downsample the image (for some ximea cameras)

        tracking_config : dict
            preprocessing_method: str, optional
               "prefilter" or "bgsub"
            tracking_method: str
                one of "centroid", "tail_angles", "eyes", "fish"
            estimator: str or class
                for closed-loop experiments: either "vigor" for embedded experiments
                    or "position" for freely-swimming ones. A custom estimator can be supplied

        recording_config : bool
            for video-recording experiments

        embedded : bool
            if not embedded, use circle calibrator
            to match the camera and projector

        dir_assets : str
            the location of assets used for stimulation (pictures, videos, models
            for closed loop etc.)

        dir_save : str
            directory where the experiment data will be saved

        metadata_animal : class
            subclass of AnimalMetadata adding information from a specific lab
            (species, genetic lines, pharmacological treatments etc.)

        metdata_general : class
            subclass of GeneralMetadata, containing lab-specific information
            (setup names, experimenter names...)

        record_stim_every: int
            if non-0 recodrds the displayed stimuli into an array which is
            saved alongside the other data.

        trigger : object
            a trigger object, synchronising stimulus presentation
            to imaging acquisition

        n_tracking_processes : int
            number of tracking processes to be used

    """

    def __init__(
        self,
        camera_config=None,
        tracking_config=None,
        recording_config=None,
        exec=True,
        # scope_triggering=None,
        **kwargs
    ):
        # Check if exist a default config file in the home (user) directory:
        default_config_file = Path.home() / "stytra_setup_config.json"
        if default_config_file.is_file():
            config = json.load(open(default_config_file))
        else:
            config = dict()
        print(config)

        # Get rest of configuration parameters from the procotol:
        try:
            extra_config = kwargs["protocol"].stytra_config
        except AttributeError:
            extra_config = dict()

        recursive_update(config, extra_config)

        print(config)
        if config["scope_triggering"] == "zmq":
            # Automatically use zmqTrigger if zmq is specified
            from stytra.triggering import ZmqTrigger

            config["scope_triggering"] = ZmqTrigger(port="5555")
        # else:
        #     class_kwargs['scope_triggering'] = scope_triggering

        app = QApplication([])
        app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

        class_kwargs = dict(app=app)
        class_kwargs.update(kwargs)
        class_kwargs.update(config)

        base = Experiment

        if "camera_config" in class_kwargs.keys():
            base = CameraExperiment
            if "tracking_config" in class_kwargs.keys():
                base = TrackingExperiment
                if not class_kwargs["tracking_config"]["embedded"]:
                    class_kwargs["calibrator"] = CircleCalibrator()
            if "recording_config" in class_kwargs.keys():
                base = SwimmingRecordingExperiment

        app_icon = QIcon()
        for size in [32, 64, 128, 256]:
            app_icon.addFile(
                pkg_resources.resource_filename(__name__, "/icons/{}.png".format(size)),
                QSize(size, size),
            )
        app.setWindowIcon(app_icon)

        pg.setConfigOptions(imageAxisOrder="row-major")

        self.exp = base(**class_kwargs)

        self.exp.start_experiment()
        if exec:
            app.exec_()


# if __name__ == "__main__":
#     import argparse
#     from pathlib import Path
#     # default_config_file = Path("~/setup_config.json")
#     #
#     # import json
#     #
#     # if default_config_file.is_file():
#     #     config = json.load(open(default_config_file))
#     # else:
#     #     config = dict()
#
#     # parser = argparse.ArgumentParser(description="Run Stytra")
#     # parser.add_argument("configuration", type=str, action="store", nargs="?", help="json", default=None)
#     # args = parser.parse_args()
#     #
#     # if args.configuration is not None:
#     #     try:
#     #         config.update(json.load(open(args.config)))
#     #     except OSError as e:
#     #         print("Config file not valid ", e)
#
#     st = Stytra()
