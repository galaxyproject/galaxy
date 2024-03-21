from galaxy.tools.expressions import evaluate
from galaxy.util.unittest_utils import skip_unless_executable


@skip_unless_executable("node")
def test_evaluate():
    input = {"script": "{return 5;}"}
    assert evaluate(None, input) == 5
