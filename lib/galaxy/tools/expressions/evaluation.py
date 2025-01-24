import json
import os
import subprocess
from typing import (
    Optional,
    TYPE_CHECKING,
)

from cwl_utils.expression import do_eval as _do_eval

from .util import find_engine

if TYPE_CHECKING:
    from cwl_utils.types import (
        CWLObjectType,
        CWLOutputType,
    )

FILE_DIRECTORY = os.path.normpath(os.path.dirname(os.path.join(__file__)))
NODE_ENGINE = os.path.join(FILE_DIRECTORY, "cwlNodeEngine.js")


def do_eval(expression: str, jobinput: "CWLObjectType", context: Optional["CWLOutputType"] = None):
    return _do_eval(
        expression,
        jobinput,
        [{"class": "InlineJavascriptRequirement"}],
        None,
        None,
        {},
        context=context,
        cwlVersion="v1.2.1",
    )


def evaluate(config, input):
    application = find_engine(config)

    default_context = {
        "engineConfig": [],
        "job": {},
        "context": None,
        "outdir": None,
        "tmpdir": None,
    }

    new_input = default_context
    new_input.update(input)

    sp = subprocess.Popen(
        [application, NODE_ENGINE], shell=False, close_fds=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE
    )
    input_str = f"{json.dumps(new_input)}\n\n"
    input_bytes = input_str.encode("utf-8")
    (stdoutdata, stderrdata) = sp.communicate(input_bytes)
    if sp.returncode != 0:
        message = f"Expression engine returned non-zero exit code on evaluation of\n{json.dumps(new_input, indent=4)}{stdoutdata}{stderrdata}"
        raise Exception(message)

    rval_raw = stdoutdata.decode("utf-8")
    return json.loads(rval_raw)
