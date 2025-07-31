import json
import os
import subprocess
from typing import (
    Optional,
)

from cwl_utils.expression import do_eval as _do_eval
from cwl_utils.types import (
    CWLObjectType,
    CWLOutputType,
)

from galaxy.tool_util_models.tool_source import JavascriptRequirement
from .util import find_engine

FILE_DIRECTORY = os.path.normpath(os.path.dirname(os.path.join(__file__)))
NODE_ENGINE = os.path.join(FILE_DIRECTORY, "cwlNodeEngine.js")


def do_eval(
    expression: str,
    jobinput: CWLObjectType,
    javascript_requirements: Optional[list[JavascriptRequirement]] = None,
    outdir: Optional[str] = None,
    tmpdir: Optional[str] = None,
    context: Optional["CWLOutputType"] = None,
):
    requirements: list[CWLObjectType] = []
    if javascript_requirements:
        for req in javascript_requirements:
            if expression_lib := req.expression_lib:
                requirements.append({"class": "InlineJavascriptRequirement", "expressionLib": expression_lib})  # type: ignore[dict-item] # very strange, a list[str] literal works
            else:
                requirements.append({"class": "InlineJavascriptRequirement"})
    else:
        requirements = [{"class": "InlineJavascriptRequirement"}]
    return _do_eval(
        expression,
        jobinput,
        requirements,
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
