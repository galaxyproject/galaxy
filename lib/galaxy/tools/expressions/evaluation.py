import json
import os
import subprocess

from .util import find_engine

FILE_DIRECTORY = os.path.normpath(os.path.dirname(os.path.join(__file__)))
NODE_ENGINE = os.path.join(FILE_DIRECTORY, "cwlNodeEngine.js")


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
        args = (json.dumps(new_input, indent=4), stdoutdata, stderrdata)
        message = "Expression engine returned non-zero exit code on evaluation of\n%s%s%s" % args
        raise Exception(message)

    rval_raw = stdoutdata.decode("utf-8")
    return json.loads(rval_raw)
