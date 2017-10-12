from PyQt5.QtWidgets import QWidget, QMainWindow, QSplitter, QVBoxLayout

from stytra.gui.control_gui import ProtocolControlWindow
from stytra.gui.display_gui import StimulusDisplayWindow
from stytra.calibration import CrossCalibrator, CircleCalibrator

from stytra.metadata import MetadataFish, MetadataGeneral
from stytra.metadata.metalist_gui import MetaListGui
from stytra.collectors import DataCollector
import qdarkstyle
import git

# imports for tracking
from stytra.hardware.video import XimeaCamera, VideoFileSource, FrameDispatcher
from stytra.tracking import QueueDataAccumulator
from stytra.tracking.tail import trace_tail_radial_sweep, trace_tail_centroid
from stytra.gui.camera_display import CameraTailSelection, CameraViewCalib
from stytra.gui.plots import MultiStreamPlot, StreamingPositionPlot
from multiprocessing import Queue, Event
from stytra.stimulation import Protocol

from stytra.stimulation.closed_loop import LSTMLocationEstimator, SimulatedLocationEstimator
from stytra.stimulation.protocols import VRProtocol, ReafferenceProtocol

from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtWidgets import QCheckBox
from stytra.metadata import MetadataCamera
import sys

from collections import namedtuple

import traceback

# imports for accumulator
import pandas as pd
import numpy as np

# imports for moving detector
from stytra.hardware.video import MovingFrameDispatcher

import os

import zmq
from stytra.dbconn import put_experiment_in_db

# this part is needed to find default arguments of functions
import inspect


def get_default_args(func):
    signature = inspect.signature(func)
    return {
        k: v.default
        for k, v in signature.parameters.items()
        if v.default is not inspect.Parameter.empty
    }


class Experiment(QMainWindow):
    sig_calibrating = pyqtSignal()
    def __init__(self, directory,
                 calibrator=None,
                 save_csv=False,
                 app=None,
                 asset_directory='',
                 debug_mode=True):
        """ A general class for running experiments

        :param directory:
        :param name:
        :param app: A QApplication in which to run the experiment
        """
        super().__init__()

        self.app = app
        self.app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

        self.metadata_general = MetadataGeneral()
        self.metadata_fish = MetadataFish()

        self.directory = directory

        if not os.path.isdir(self.directory):
            os.makedirs(self.directory)
        print('Saving into '+self.directory )

        self.save_csv = save_csv

        self.dc = DataCollector(self.metadata_general, self.metadata_fish,
                                folder_path=self.directory, use_last_val=True)

        self.asset_folder = asset_directory

        self.debug_mode = debug_mode
        if not self.debug_mode:
            self.check_if_committed()

        self.window_display = StimulusDisplayWindow(experiment=self)
        self.widget_control = ProtocolControlWindow(self.window_display,
                                                    self.debug_mode)

        self.metadata_gui = MetaListGui([self.metadata_general,
                                         self.metadata_fish])
        self.widget_control.combo_prot.currentIndexChanged.connect(self.change_protocol)
        self.widget_control.spn_n_repeats.valueChanged.connect(self.change_protocol)

        self.widget_control.button_metadata.clicked.connect(self.metadata_gui.show)
        self.widget_control.button_toggle_prot.clicked.connect(self.toggle_protocol)

        # Connect the display window to the metadata collector
        self.dc.add_data_source('stimulus', 'display_params',
                                self.window_display, 'display_params',
                                use_last_val=True)

        self.widget_control.reset_ROI()

        if calibrator is None:
            self.calibrator = CrossCalibrator()
        else:
            self.calibrator = calibrator

        self.window_display.widget_display.calibrator = self.calibrator
        self.widget_control.button_show_calib.clicked.connect(self.toggle_calibration)
        self.dc.add_data_source('stimulus', 'mm per px',
                                self.calibrator, 'mm_px', use_last_val=True)
        self.dc.add_data_source('stimulus', 'calibration_pattern_length_mm',
                                self.calibrator, 'length_mm', use_last_val=True)
        self.dc.add_data_source('stimulus', 'calibration_pattern_length_px',
                                self.calibrator, 'length_px',
                                use_last_val=True)

        self.dc.add_data_source('general', 't_protocol_start',
                                self, 'protocol', 't_start',
                                use_last_val=False)

        self.dc.add_data_source('general', 't_protocol_end',
                                self, 'protocol', 't_end',
                                use_last_val=False)

        self.dc.add_data_source('general', 'is_protocol_completed',
                                self, 'protocol', 'completed',
                                use_last_val=False)

        self.widget_control.spin_calibrate.valueChanged.connect(
            self.calibrator.set_physical_scale)
        self.widget_control.spin_calibrate.setValue(self.calibrator.length_mm)

        self.dc.add_data_source('stimulus', 'log', self, 'protocol', 'log', use_last_val=False)

        self.protocol = None
        self.init_ui()
        self.show()

    def init_ui(self):
        self.setCentralWidget(self.widget_control)

    def toggle_protocol(self):
        if self.protocol.running:
            self.end_protocol()
            self.widget_control.button_toggle_prot.setText("▶")
        else:
            self.start_protocol()
            self.widget_control.button_toggle_prot.setText("■")

    def change_protocol(self, _):
        # TODO implement GUI for protocol params
        Protclass = self.widget_control.combo_prot.prot_classdict[
            self.widget_control.combo_prot.currentText()]
        n_repeats = self.widget_control.spn_n_repeats.value()
        self.set_protocol(Protclass(n_repeats=n_repeats, experiment=self))
        self.reconfigure_ui()

    def reconfigure_ui(self):
        pass

    def set_protocol(self, protocol):
        self.protocol = protocol
        self.protocol.reset()
        self.window_display.widget_display.set_protocol(self.protocol)
        self.protocol.sig_timestep.connect(self.update_progress)
        self.protocol.sig_protocol_finished.connect(self.end_protocol)
        self.widget_control.progress_bar.setMaximum(int(self.protocol.duration))
        self.widget_control.progress_bar.setValue(0)

    def update_progress(self, i_stim):
        self.widget_control.progress_bar.setValue(int(self.protocol.t))

    def check_if_committed(self):
        """ Checks if the version of stytra used to run the experiment is commited,
        so that for each experiment it is known what code was used to record it

        :return:
        """
        repo = git.Repo(search_parent_directories=True)
        git_hash = repo.head.object.hexsha
        self.dc.add_data_source('general', 'git_hash', git_hash)
        self.dc.add_data_source('general', 'program_name', __file__)

        if len(repo.git.diff('HEAD~1..HEAD',
                             name_only=True)) > 0:
            print('The following files contain uncommitted changes:')
            print(repo.git.diff('HEAD~1..HEAD', name_only=True))
            raise PermissionError(
                'The project has to be committed before starting!')

    def show_stimulus_screen(self, full_screen=True):
        self.window_display.show()
        if full_screen:
            try:
                self.window_display.windowHandle().setScreen(self.app.screens()[1])
                self.window_display.showFullScreen()
            except IndexError:
                print('Second screen not available')

    def start_protocol(self):
        self.protocol.start()

    def end_protocol(self, do_not_save=None):
        self.protocol.end()
        if not do_not_save:
            if not self.debug_mode:
                db_id = put_experiment_in_db(self.dc.get_full_dict())
                self.dc.add_data_source('general', 'db_id', db_id)

            self.dc.save(save_csv=self.save_csv)
        self.protocol.reset()

    def closeEvent(self, *args, **kwargs):
        self.end_protocol(do_not_save=True)
        self.app.closeAllWindows()

    def toggle_calibration(self):
        self.calibrator.toggle()
        if self.calibrator.enabled:
            self.widget_control.button_show_calib.setText('Hide calibration')
        else:
            self.widget_control.button_show_calib.setText('Show calibration')
        self.window_display.widget_display.update()
        self.sig_calibrating.emit()


class LightsheetExperiment(Experiment):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.zmq_context = zmq.Context()
        self.zmq_socket = self.zmq_context.socket(zmq.REP)

        self.chk_lightsheet = QCheckBox("Wait for lightsheet")
        self.chk_lightsheet.setChecked(False)

        self.widget_control.layout.addWidget(self.chk_lightsheet, 0)

        self.lightsheet_config = dict()
        self.dc.add_data_source('imaging', 'lightsheet_config', self, 'lightsheet_config')

    def start_protocol(self):
        # Start only when received the GO signal from the lightsheet
        if self.chk_lightsheet.isChecked():
            self.zmq_socket.bind("tcp://*:5555")
            print('bound socket')
            self.lightsheet_config = self.zmq_socket.recv_json()
            print('received config')
            print(self.lightsheet_config)
            # send the duration of the protocol so that
            # the scanning can stop
            self.zmq_socket.send_json(self.protocol.duration)
        super().start_protocol()


class CameraExperiment(Experiment):
    def __init__(self, *args, video_file=None, **kwargs):
        """

        :param args:
        :param video_file: if not using a camera, the video
        file for the test input
        :param kwargs:
        """
        super().__init__(*args, **kwargs)
        self.frame_queue = Queue(500)
        self.gui_frame_queue = Queue()
        self.finished_sig = Event()

        self.gui_refresh_timer = QTimer()
        self.gui_refresh_timer.setSingleShot(False)

        self.metadata_camera = MetadataCamera()
        self.dc.add_data_source(self.metadata_camera)

        if video_file is None:
            self.control_queue = Queue()
            self.camera = XimeaCamera(self.frame_queue,
                                      self.finished_sig,
                                      self.control_queue)
        else:
            self.control_queue = None
            self.camera = VideoFileSource(self.frame_queue,
                                          self.finished_sig,
                                          video_file)

        self.frame_dispatcher = None

    def go_live(self):
        self.camera.start()
        self.gui_refresh_timer.start(1000//60)
        if self.frame_dispatcher is not None:
            self.frame_dispatcher.start()
        sys.excepthook = self.excepthook

    def closeEvent(self, *args, **kwargs):
        super().closeEvent(*args, **kwargs)
        self.finished_sig.set()
        # self.camera.join(timeout=1)
        self.camera.terminate()
        print('Camera process terminated')
        if self.frame_dispatcher is not None:
            self.frame_dispatcher.terminate()
            print('Frame dispatcher terminated')
        self.gui_refresh_timer.stop()


class TailTrackingExperiment(CameraExperiment):
    def __init__(self, *args,
                 tracking_method='angle_sweep',
                 tracking_method_parameters=None,
                 motion_estimation=None, motion_estimation_parameters=None,
                 **kwargs):
        """ An experiment which contains tail tracking,
        base for any experiment that tracks behaviour or employs
        closed loops

        :param args:
        :param tracking_method: the method used to track the tail
        :param kwargs:
        """
        super().__init__(*args, **kwargs)
        self.metadata_fish.embedded = True

        # infrastructure for processing data from the camera
        self.processing_parameter_queue = Queue()
        self.tail_position_queue = Queue()

        dict_tracking_functions = dict(angle_sweep=trace_tail_radial_sweep,
                                       centroid=trace_tail_centroid)

        current_tracking_method_parameters = get_default_args(dict_tracking_functions[tracking_method])
        if tracking_method_parameters is not None:
            current_tracking_method_parameters.update(tracking_method_parameters)

        self.frame_dispatcher = FrameDispatcher(frame_queue=self.frame_queue,
                                                gui_queue=self.gui_frame_queue,
                                                processing_function=dict_tracking_functions[tracking_method],
                                                processing_parameter_queue=self.processing_parameter_queue,
                                                finished_signal=self.finished_sig,
                                                output_queue=self.tail_position_queue,
                                                gui_framerate=20,
                                                print_framerate=False)

        self.data_acc_tailpoints = QueueDataAccumulator(self.tail_position_queue,
                                                        header_list=['tail_sum'] +
                                                        ['theta_{:02}'.format(i)
                                                         for i in range(
                                                            current_tracking_method_parameters['n_segments'])])

        self.camera_viewer = CameraTailSelection(
            tail_start_points_queue=self.processing_parameter_queue,
            camera_queue=self.gui_frame_queue,
            tail_position_data=self.data_acc_tailpoints,
            update_timer=self.gui_refresh_timer,
            control_queue=self.control_queue,
            camera_parameters=self.metadata_camera,
            tracking_params=current_tracking_method_parameters)

        self.widget_control.layout.insertWidget(0, self.camera_viewer)

        self.dc.add_data_source('tracking',
                                'tail_position', self.camera_viewer, 'roi_dict')
        self.camera_viewer.reset_ROI()

        # start the processes and connect the timers
        self.gui_refresh_timer.timeout.connect(
            self.data_acc_tailpoints.update_list)

        if motion_estimation == 'LSTM':
            lstm_name = motion_estimation_parameters['model']
            del motion_estimation_parameters['model']
            self.position_estimator = LSTMLocationEstimator(self.data_acc_tailpoints,
                                                            self.asset_folder + '/' +
                                                            lstm_name,
                                                            **motion_estimation_parameters)

        self.main_layout = QSplitter()
        self.monitoring_widget = QWidget()
        self.monitoring_layout = QVBoxLayout()
        self.monitoring_widget.setLayout(self.monitoring_layout)

        self.stream_plot = MultiStreamPlot()

        self.monitoring_layout.addWidget(self.stream_plot)
        self.gui_refresh_timer.timeout.connect(self.stream_plot.update)

        self.stream_plot.add_stream(self.data_acc_tailpoints,
                                    ['tail_sum', 'theta_01'])

        self.main_layout.addWidget(self.monitoring_widget)
        self.main_layout.addWidget(self.widget_control)
        self.setCentralWidget(self.main_layout)

        self.positionPlot = None

        self.go_live()

    def start_protocol(self):
        self.data_acc_tailpoints.reset()
        super().start_protocol()

    def end_protocol(self, *args, **kwargs):
        self.dc.add_data_source('behaviour', 'tail',
                                self.data_acc_tailpoints.get_dataframe())
        self.dc.add_data_source('behaviour', 'vr',
                                self.position_estimator.log.get_dataframe())
        # temporary removal of dynamic log as it is not correct
        self.dc.add_data_source('stimulus', 'dynamic_parameters',
                                 self.protocol.dynamic_log.get_dataframe())
        super().end_protocol(*args, **kwargs)
        try:
            self.position_estimator.reset()
            self.position_estimator.log.reset()
        except AttributeError:
            pass

    def set_protocol(self, protocol):
        super().set_protocol(protocol)
        self.protocol.sig_protocol_started.connect(self.data_acc_tailpoints.reset)

    def reconfigure_ui(self):
        if isinstance(self.protocol, VRProtocol) and self.positionPlot is None:
            self.positionPlot = StreamingPositionPlot(data_accumulator=self.protocol.dynamic_log)
            self.monitoring_layout.addWidget(self.positionPlot)
            self.gui_refresh_timer.timeout.connect(self.positionPlot.update)
            self.stream_plot.add_stream(self.position_estimator.log,
                                        self.position_estimator.log.header_list[1:])


    def excepthook(self, exctype, value, tb):
        traceback.print_tb(tb)
        print('{0}: {1}'.format(exctype, value))
        self.finished_sig.set()
        self.camera.terminate()
        self.frame_dispatcher.terminate()


class SimulatedVRExperiment(Experiment):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        BoutTuple = namedtuple('BoutTuple', ['t', 'dx', 'dy', 'theta'])
        bouts = [
            BoutTuple(4, 5, 1, 0),
            BoutTuple(10, 0, 0, -np.pi/2),
            BoutTuple(12, 5, 1, 0),
            BoutTuple(18, 0, 0, np.pi/2),
            BoutTuple(20, 5, 1, 0)
        ]
        self.set_protocol(VRProtocol(experiment=self,
                                     background_image='arrow.png',
                                     velocities=[
                                     (8, 0, 5),
                                     (8, 5, 0),
                                     (8, 0, 5)]
                                     ))
        self.position_estimator = SimulatedLocationEstimator(bouts)
        self.position_plot = StreamingPositionPlot(data_accumulator=self.protocol.dynamic_log,
                                                   n_points=1000)
        self.main_layoutiem = QSplitter()
        self.main_layoutiem.addWidget(self.position_plot)
        self.main_layoutiem.addWidget(self.widget_control)
        self.setCentralWidget(self.main_layoutiem)

        self.gui_refresh_timer = QTimer()
        self.gui_refresh_timer.setSingleShot(False)
        self.gui_refresh_timer.start()
        self.gui_refresh_timer.timeout.connect(self.position_plot.update)

    def end_protocol(self, do_not_save=None):
        super().end_protocol(do_not_save)
        self.position_estimator.reset()


class MovementRecordingExperiment(CameraExperiment):
    """ Experiment where the fish is recorded while it is moving

    """
    def __init__(self, *args, **kwargs):
        self.framestart_queue = Queue()
        self.splitter = QSplitter()
        self.camera_view = CameraViewCalib(camera_queue=self.gui_frame_queue,
                                           update_timer=self.gui_refresh_timer,
                                           control_queue=self.control_queue,
                                           camera_parameters=self.metadata_camera)
        super().__init__(*args, **kwargs)
        self.calibrator = CircleCalibrator()

        self.frame_dispatcher = MovingFrameDispatcher(self.frame_queue,
                                                      self.gui_frame_queue,
                                                      self.finished_sig,
                                                      output_queue=self.record_queue,
                                                      framestart_queue=self.framestart_queue,
                                                      signal_start_rec=self.start_rec_sig,
                                                      gui_framerate=30)
        self.go_live()

    def init_ui(self):
        self.setCentralWidget(self.splitter)
        self.splitter.addWidget(self.camera_view)
        self.splitter.addWidget(self.widget_control)