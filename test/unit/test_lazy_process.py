import os
import tempfile
import time

from galaxy.util.lazy_process import LazyProcess


def test_lazy_process():
    t = tempfile.NamedTemporaryFile()
    os.remove(t.name)
    lazy_process = LazyProcess(["bash", "-c", "touch %s; sleep 100" % t.name])
    assert not os.path.exists(t.name)
    lazy_process.start_process()
    time.sleep(.02)
    assert lazy_process.process.poll() is None
    assert os.path.exists(t.name)
    lazy_process.shutdown()
    time.sleep(.02)
    assert lazy_process.process.poll()
