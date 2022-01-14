import numpy as np
from stytra.hardware.video.cameras.interface import Camera, CameraError

try:
    import PySpin
except ImportError:
    pass

import logging
logging.basicConfig(filename='DS.log', level=logging.INFO)

class DoubleSpinnakerCamera(Camera):
    """Class for simple control of 2 Point Grey camera simultaneously.
    Uses Spinnaker API. Module documentation `here
    <https://www.flir.com/products/spinnaker-sdk/>`_.
     Note roi is [x, y, width, height]
    """

    def __init__(self, **kwargs):
        logging.info("[DS] init")
        super().__init__(**kwargs)
        self.system = PySpin.System.GetInstance()
        self.cams = self.system.GetCameras()
        assert (self.cams.GetSize()==2)
        logging.info("[DS] init found 2 cams.")
        self.cam1 = self.cams[0]
        self.cam2 = self.cams[1]
        self.cams = [self.cam1, self.cam2]
        for cam in self.cams:
            assert isinstance(cam, PySpin.CameraPtr)
        logging.info("[DS] all cams are Ptr cams")
            
        self.cams_info = [{},{}]
        for i, cam in enumerate(self.cams):
            nodemap = cam.GetTLDeviceNodeMap()
            node_device_information = PySpin.CCategoryPtr(
                nodemap.GetNode('DeviceInformation')
            )
            features = node_device_information.GetFeatures()
            
            for feature in features:
                node_feature = PySpin.CValuePtr(feature)
                self.cams_info[i][node_feature.GetName()] = node_feature.ToString()
        logging.info(f"[DS] cams : {self.cams_info}")
        
        self.cam_names = []
        for i in range(len(self.cams_info)):
            self.cam_names.append(
                self.cams_info[i]['DeviceModelName'].split(" ")[0]
            )
        logging.info(f"[DS] cams : {self.cam_names}")
        
        logging.info("[DS] done with init")
        
    def open_camera(self):
        logging.info("[DS] open")
        msgs = []
        for cam, name in zip(self.cams, self.cam_names):
            msg = self.open_single_camera(cam, name)
            msgs += msg
        #msg2 = self.open_single_camera(self.cam2)
        return msgs

    def open_single_camera(self, cam, name):
        logging.info(f"[DS] opening camera {name}")
        messages = []
        cam.Init()
        nodemap = cam.GetNodeMap()

        # SET TO CONTINUOUS ACQUISITION MODE
        acquisition_mode_node = PySpin.CEnumerationPtr(
            nodemap.GetNode("AcquisitionMode")
        )
        if not PySpin.IsAvailable(acquisition_mode_node) or not PySpin.IsWritable(
            acquisition_mode_node
        ):
            messages.append(
                "W: May not be able to set acquisition mode to continuous (enum retrieval)."
            )

        # Retrieve entry node from enumeration node
        acquisition_mode_continuous_node = acquisition_mode_node.GetEntryByName(
            "Continuous"
        )
        if not PySpin.IsAvailable(
            acquisition_mode_continuous_node
        ) or not PySpin.IsReadable(acquisition_mode_continuous_node):
            messages.append(
                "W: Unable to set acquisition mode to continuous (entry retrieval)."
            )
        acquisition_mode_continuous = acquisition_mode_continuous_node.GetValue()
        acquisition_mode_node.SetIntValue(acquisition_mode_continuous)
        logging.info("[DS] acquisition mode set to continuous")

        '''
        # Set ROI first if applicable (framerate limits depend on it)
        try:
            # Note set width/height before x/y offset because upon
            # initialization max offset is 0 because full frame size is assumed
            for i, (s, o) in enumerate(
                zip(["Width", "Height"], ["OffsetX", "OffsetY"])
            ):

                roi_node = PySpin.CIntegerPtr(nodemap.GetNode(s))
                # If no ROI is specified, use full frame:
                if roi[2 + i] == -1:
                    value_to_set = roi_node.GetMax()
                else:
                    value_to_set = roi[2 + i]
                inc = roi_node.GetInc()
                if np.mod(value_to_set, inc) != 0:
                    value_to_set = (value_to_set // inc) * inc
                    messages.append(
                        "W: Need to set width in increments of {0}, resetting to {1}.".format(
                            inc, value_to_set
                        )
                    )
                roi_node.SetValue(value_to_set)

                # offset
                offset_node = PySpin.CIntegerPtr(nodemap.GetNode(o))
                if roi[0 + i] == -1:
                    off_to_set = offset_node.GetMin()
                else:
                    off_to_set = roi[0 + i]
                offset_node.SetValue(off_to_set)

        except Exception as ex:
            messages.append("E:Could not set ROI. Exception: {0}.".format(ex))
        '''

        # Enabling framerate control from Stytra

        # Disabling auto frame rate
        self.acquisition_rate_node = cam.AcquisitionFrameRate
        node_acquisition_frame_rate_control_enable = PySpin.CBooleanPtr(
            nodemap.GetNode("AcquisitionFrameRateEnable")
        )
        if PySpin.IsAvailable(
            node_acquisition_frame_rate_control_enable
        ):  # older simpler api
            cam.AcquisitionFrameRateEnable.SetValue(True)
        else:  # newer more complex api
            frame_rate_auto_node = PySpin.CEnumerationPtr(
                nodemap.GetNode("AcquisitionFrameRateAuto")
            )

            node_frame_rate_auto_off = frame_rate_auto_node.GetEntryByName("Off")

            frame_rate_auto_off = node_frame_rate_auto_off.GetValue()
            frame_rate_auto_node.SetIntValue(frame_rate_auto_off)
            enable_rate_mode = PySpin.CBooleanPtr(
                nodemap.GetNode("AcquisitionFrameRateEnabled")
            )
            if not PySpin.IsAvailable(enable_rate_mode) or not PySpin.IsWritable(
                enable_rate_mode
            ):
                messages.append(
                    "W:enable_rate_mode not available/writable. Aborting..."
                )
            try:
                enable_rate_mode.SetValue(True)
            except PySpin.SpinnakerException as ex:
                messages.append("E:Could not enable frame rate: {0}".format(ex))

            # Check to make sure frame rate is now writeable
            if self.acquisition_rate_node.GetAccessMode() != PySpin.RW:
                messages.append("W:Frame rate mode was not set to read&write.")

        # Determine frame rate min/max (this depends on ROI)
        self.rate_max = self.acquisition_rate_node.GetMax()
        self.rate_min = self.acquisition_rate_node.GetMin()
        
        logging.info("[DS] framerate control enabled")
        '''
        # Making exposure controllable
        # Turn off auto exposure
        exposure_auto_node = cam.ExposureAuto
        if exposure_auto_node.GetAccessMode() != PySpin.RW:
            messages.append("W:Unable to disable automatic exposure. Aborting...")
        exposure_auto_node.SetValue(PySpin.ExposureAuto_Off)
        # Check for availability/writeability of exposure time
        self.exposure_time_node = cam.ExposureTime
        if self.exposure_time_node.GetAccessMode() != PySpin.RW:
            messages.append("W:Exposure time is not read/write")
        self.exposure_max = self.exposure_time_node.GetMax()
        self.exposure_min = self.exposure_time_node.GetMin()
        logging.info("[DS] exposure control enabled")

        # Making gain controllable
        # Turn off auto-gain
        gain_auto_node = cam.GainAuto
        if gain_auto_node.GetAccessMode() != PySpin.RW:
            messages.append("W:Unable to disable automatic gain.")
        gain_auto_node.SetValue(PySpin.GainAuto_Off)
        self.gain_node = cam.Gain
        self.gain_min = self.gain_node.GetMin()
        self.gain_max = self.gain_node.GetMax()
        logging.info("[DS] gain control enabled")
        '''
        # Starting acquisition
        cam.BeginAcquisition()
        messages.append(f"I:Opened Point Grey camera {name}")
        return messages

    def set(self, param, val):
        """
        Parameters
        ----------
        param : string name
        val : value in appropriate format for parameter
        Returns string
        -------
        """
        logging.info(f"[DS] set {param}={val}")
        messages = []
        try:
            if param == "exposure":  # sent in ms
                '''
                # camera wants exposure in us:
                exposure_time_to_set = val * 1000  # convert to microseconds
                if exposure_time_to_set > self.exposure_max:
                    messages.append(
                        "E:exposure greater than max of {:3.1f}".format(
                            self.exposure_max / 1000
                        )
                    )
                    exposure_time_to_set = self.exposure_max
                elif exposure_time_to_set < self.exposure_min:
                    messages.append(
                        "E:exposure less than min of {:3.1f}".format(
                            self.exposure_min / 1000
                        )
                    )
                    exposure_time_to_set = self.exposure_min
                self.exposure_time_node.SetValue(exposure_time_to_set)
                '''
                messages.append("E:exposure not controllable with DoubleSpinnaker")

            if param == "gain":
                '''
                gain_to_set = val
                if gain_to_set > self.gain_max:
                    messages.append(
                        "E:gain greater than max of {:3.1f}".format(self.gain_max)
                    )
                    gain_to_set = self.gain_max
                elif gain_to_set < self.gain_min:
                    messages.append(
                        "E:gain less than min of {:3.1f}".format(self.gain_min)
                    )
                    gain_to_set = self.gain_min
                if self.gain_node.GetAccessMode() != PySpin.RW:
                    messages.append("E:gain is not r/w - another camera window open?")
                self.gain_node.SetValue(gain_to_set)
                '''
                messages.append("E:gain not controllable with DoubleSpinnaker")

            if param == "framerate":
                '''
                frame_rate = val
                if frame_rate > self.rate_max:
                    messages.append(
                        "E:fps greater than max of {:3.1f}".format(self.rate_max)
                    )
                    frame_rate = self.rate_max
                elif frame_rate < self.rate_min:
                    messages.append(
                        "E:fps less than min of {:3.1f}".format(self.rate_min)
                    )
                    frame_rate = self.rate_min
                self.acquisition_rate_node.SetValue(frame_rate)
                '''
                messages.append("E:framerate not controllable with DoubleSpinnaker")

        except PySpin.SpinnakerException as ex:
            err = "E: SpinnakerCamera.set() error: {0}".format(ex)
            messages.append(err)
            # return err
        return messages

    def read(self):
        logging.debug("[DS] read")
        try:
            #  Retrieve next received image
            image_result1 = self.cam1.GetNextImage()
            image_result2 = self.cam2.GetNextImage()

            #  Ensure image completion
            if image_result1.IsIncomplete() or image_result2.IsIncomplete():
                return

            else:
                image_converted1 = np.array(
                    image_result1.GetData(), dtype="uint8"
                ).reshape((image_result1.GetHeight(), image_result1.GetWidth()))
                #  Images retrieved directly from the camera (i.e. non-converted
                #  images) need to be released in order to keep from filling the
                #  buffer.
                image_result1.Release()
                image_converted2 = np.array(
                    image_result2.GetData(), dtype="uint8"
                ).reshape((image_result2.GetHeight(), image_result2.GetWidth()))
                #  Images retrieved directly from the camera (i.e. non-converted
                #  images) need to be released in order to keep from filling the
                #  buffer.
                image_result2.Release()
                #return [image_converted1, image_converted2]
                #return image_converted2
                logging.debug("[DS] images transformed")
                return stack(image_converted1, image_converted2)

        except PySpin.SpinnakerException as ex:
            raise CameraError("Frame not read")

    def release(self):
        logging.info("[DS] release")
        self.cam1.EndAcquisition()
        self.cam1.DeInit()
        del self.cam1
        self.cam2.EndAcquisition()
        self.cam2.DeInit()
        del self.cam2
        del self.cams
        self.system.ReleaseInstance()
        
        


        
        
        
def stack(im1, im2):
    """Stack the 2 images together."""
    w1, h1 = im1.shape
    w2, h2 = im2.shape
    logging.debug(f"[DS] shapes = {(w1, h1)} . {(w2, h2)}")
    
    if ( (w1+w2)*max(h1,h2) ) < ( max(w1,w2)*(h1+h2) ):
        w = w1+w2
        h = max(h1,h2)
        logging.debug(f"[DS] output shape = {(w, h)}")
        img = np.zeros((w,h), dtype="uint8")
        img[0:w1, 0:h1] = im1
        img[w1:w1+w2, 0:h2] = im2
    else:
        w = max(w1,w2)
        h = h1+h2
        logging.debug(f"[DS] output shape = {(w, h)}")
        img = np.zeros((w,h), dtype="uint8")
        img[0:w1, 0:h1] = im1
        img[0:w2, h1:h1+h2] = im2
    return img