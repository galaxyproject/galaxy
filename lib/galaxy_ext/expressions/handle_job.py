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
    from cwl_utils import expression
except ImportError:
    expression = None  # type: ignore[assignment]

from galaxy.tools.expressions import evaluate

logging.basicConfig()
log = logging.getLogger(__name__)


def run(environment_path=None):
    if expression is None:
        raise Exception("Python library cwl-utils must be available to evaluate expressions.")

    if environment_path is None:
        environment_path = os.environ.get("GALAXY_EXPRESSION_INPUTS")
    with open(environment_path) as f:
        raw_inputs = json.load(f)

    outputs = raw_inputs["outputs"]
    inputs = raw_inputs.copy()
    del inputs["outputs"]
    result = evaluate(None, inputs)

    if "__error_message" in result:
        raise Exception(result["__error_message"])
    for output in outputs:
        path = output["path"]
        from_expression = output["from_expression"]
        # if it is just a simple value, short-cut all the interpolation
        # interpolate seems to fail with None values so this worksaround
        # that for now.
        if from_expression in result:
            output_value = result[from_expression]
        else:
            from_expression = f"$({from_expression})"
            output_value = expression.interpolate(from_expression, result)
        with open(path, "w") as f:
            json.dump(output_value, f)
