"""
Execute an external process to evaluate expressions for Galaxy jobs.

Galaxy should be importable on sys.path .
"""
import json
import logging
import os
import sys
import warnings

# insert *this* galaxy before all others on sys.path
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)))
warnings.filterwarnings("ignore", message=r"[\n.]DEPRECATION: Python 2", module="cwltool")

try:
    from cwltool import expression
except ImportError:
    expression = None

from galaxy.tools.expressions import evaluate

logging.basicConfig()
log = logging.getLogger(__name__)


def run(environment_path=None):
    if expression is None:
        raise Exception("Python library cwltool must be available to evaluate expressions.")

    if environment_path is None:
        environment_path = os.environ.get("GALAXY_EXPRESSION_INPUTS")
    with open(environment_path) as f:
        raw_inputs = json.load(f)

    outputs = raw_inputs["outputs"]
    inputs = raw_inputs.copy()
    del inputs["outputs"]

    result = evaluate(None, inputs)

    for output in outputs:
        path = output["path"]
        from_expression = "$(" + output["from_expression"] + ")"
        output_value = expression.interpolate(from_expression, result)
        with open(path, "w") as f:
            json.dump(output_value, f)
