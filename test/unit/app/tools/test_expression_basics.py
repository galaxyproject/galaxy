from galaxy.tools.expressions import evaluate


def test_evaluate():
    input = {"script": "{return 5;}"}
    assert evaluate(None, input) == 5
