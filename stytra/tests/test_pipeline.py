from stytra.tracking.pipelines import Pipeline, ImageToDataNode, SourceNode
from lightparam import Param
from collections import namedtuple


class TestNode(ImageToDataNode):
    def __init__(self, *args, **kwargs):
        super().__init__("testnode", *args, **kwargs)

    def _process(self, input, a:Param(1)):
        if self._output_type is None:
            self._output_type = namedtuple("o", "inp par")
        else:
            self._output_type_changed = False
        return [], self._output_type(par=a, inp=input)


class TestPipeline(Pipeline):
    def __init__(self):
        super().__init__()
        self.tp = TestNode()
        self.tp.parent = self.root


def test_a_pipeline():
    p = TestPipeline()
    p.setup()
    tt = namedtuple("o", "inp par")
    assert p.run() == ([], tt(None, 1))
    ser = p.serialize_params()
    ser["/source/testnode"]["a"] = 2
    p.deserialize_params(ser)
    assert p.run() == ([], tt(None, 2))