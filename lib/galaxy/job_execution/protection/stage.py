"""Entry point run on the compute host to stage and clean up protected job inputs.

``galaxy-protected-stage stage-in <plan>`` runs before the tool, outside of any tool
container. ``cleanup-inputs`` runs right after the tool, and ``cleanup`` once the
outputs have been collected.
"""

import argparse
import logging
import os
import sys
import traceback

from galaxy.job_execution.protection import (
    load_runtime,
    ProtectionError,
    ProtectionPlan,
)

log = logging.getLogger(__name__)

COMMANDS = ("stage-in", "cleanup-inputs", "cleanup")
# Read by Galaxy when the tool never ran (see BaseJobRunner._finish_or_resubmit_job).
SETUP_FAILURE_FILE = os.path.join("metadata", "outputs_populated", "traceback.txt")
# Read by Galaxy when finishing a protected job.
CLEANUP_FAILURE_FILE = os.path.join("metadata", "outputs_populated", "protection_cleanup_failed")


def _report(job_directory: str, relative_path: str, message: str) -> None:
    path = os.path.join(job_directory, relative_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(f"{message}\n")


def run(command: str, plan_path: str) -> int:
    plan = ProtectionPlan.read(plan_path)
    runtime = load_runtime(plan)
    try:
        if command == "stage-in":
            runtime.stage_inputs()
        elif command == "cleanup-inputs":
            runtime.cleanup_inputs()
        else:
            runtime.cleanup()
    except Exception as e:
        message = str(e) if isinstance(e, ProtectionError) else f"Unexpected error ({type(e).__name__})"
        if command == "stage-in":
            message = f"Could not decrypt the protected inputs of this job: {message}"
            _report(plan.job_directory, SETUP_FAILURE_FILE, message)
        else:
            message = f"Could not remove the decrypted data of this job: {message}"
            _report(plan.job_directory, CLEANUP_FAILURE_FILE, message)
        print(message, file=sys.stderr)
        traceback.print_exc()
        return 1
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("plan_path")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)
    sys.exit(run(args.command, args.plan_path))


if __name__ == "__main__":
    main()
