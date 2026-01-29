import os

EXPRESSION_SCRIPT_NAME = "_evaluate_expression_.py"
EXPRESSION_SCRIPT_CALL = f"python {EXPRESSION_SCRIPT_NAME}"


def write_evalute_script(in_directory):
    """Responsible for writing the script that evaluates expressions
    in Galaxy jobs.
    """
    script = os.path.join(in_directory, EXPRESSION_SCRIPT_NAME)
    with open(script, "w") as f:
        f.write("from galaxy_ext.expressions.handle_job import run; run()")

    return script
