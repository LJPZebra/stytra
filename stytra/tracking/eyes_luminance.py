import numpy as np
from lightparam import Param
from stytra.tracking.pipelines import ImageToDataNode, NodeOutput
from collections import namedtuple



class EyeLumTrackingMethod(ImageToDataNode):
    """Eyes tracking method based on average pixel values."""

    name = "eyesLum"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="eyesLum_tracking", **kwargs)

        headers = [
                    "mean_L",  # mean luminance in left roi
                    "mean_R",  # mean luminance in right roi
                    "std_L",  # std luminance in left roi
                    "std_R",  # std luminance in left roi
                    "mean_tot",  # mean luminance in the entire image
                    "std_tot",  # std luminance in the entire image
                    ]

        self._output_type = namedtuple("t", headers)

        self.monitored_headers = ["mean_L", "mean_R"]

        self.data_log_name = "eyeLum_track"

    def _process(
        self,
        im,
        L_wnd_pos: Param((129, 20), gui=False),
        R_wnd_pos: Param((429, 100), gui=False),
        L_wnd_dim: Param((14, 22), gui=False),
        R_wnd_dim: Param((14, 22), gui=False),
        **extraparams
    ):
        """
        Parameters                                   # ??
        ----------
        im :
            image (numpy array);
        L_wnd_pos :
            position of the window on the left eyes (x, y);
        R_wnd_pos :
            position of the window on the right eyes (x, y);
        L_wnd_dim :
            dimension of the window on the left eyes (w, h);
        R_wnd_dim :
            dimension of the window on the right eyes (w, h);
        Returns
        -------
        """
        message = ""

        Lim = im[
                    L_wnd_pos[1] : L_wnd_pos[1] + L_wnd_dim[1],
                    L_wnd_pos[0] : L_wnd_pos[0] + L_wnd_dim[0],
                ]
        Rim = im[
                    R_wnd_pos[1] : R_wnd_pos[1] + R_wnd_dim[1],
                    R_wnd_pos[0] : R_wnd_pos[0] + R_wnd_dim[0],
                ]
        
        res = [
                np.mean(Lim),
                np.mean(Rim),
                np.std(Lim),
                np.std(Rim),
                np.mean(im),
                np.std(im),
                ]


        return NodeOutput([message], self._output_type(*res))


