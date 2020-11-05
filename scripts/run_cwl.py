#!/usr/bin/env python

import argparse
import json
import os
import sys

from bioblend import galaxy

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

from galaxy.tool_util.cwl.runnable import get_outputs
from galaxy.version import VERSION
from galaxy_test.base.populators import (  # noqa: I100,I202
    CwlPopulator,
    GiDatasetPopulator,
    GiHttpMixin,
    GiWorkflowPopulator,
)

DESCRIPTION = """Simple CWL runner script."""


def collect_outputs(cwl_run, output_names, output_directory=None, outdir=os.getcwd()):
    outputs = {}
    for output_name in output_names:
        cwl_output = cwl_run.get_output_as_object(output_name, download_folder=outdir)
        outputs[output_name] = cwl_output
    return outputs


def main(argv=None):
    """Entry point for workflow driving."""
    arg_parser = argparse.ArgumentParser(description=DESCRIPTION)
    arg_parser.add_argument("--api_key", default="testmasterapikey")
    arg_parser.add_argument("--host", default="http://localhost:8080/")
    arg_parser.add_argument("--outdir", default=".")
    arg_parser.add_argument("--quiet", action="store_true")
    arg_parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}~CWL")
    arg_parser.add_argument("--cwd", default=os.getcwd())
    arg_parser.add_argument("tool", metavar="TOOL", help="tool or workflow")
    arg_parser.add_argument("job", metavar="JOB", help="job")

    args = arg_parser.parse_args(argv)

    gi = galaxy.GalaxyInstance(args.host, args.api_key)
    i = GiHttpMixin()
    i._gi = gi
    response = i._get("whoami")
    if response.json() is None:
        email = "cwluser@example.com"
        all_users = i._get("users").json()
        try:
            test_user = [user for user in all_users if user["email"] == email][0]
        except IndexError:
            data = dict(
                email=email,
                password="testpass",
                username="cwluser",
            )
            test_user = i._post("users", data).json()

        api_key = i._post(f"users/{test_user['id']}/api_key").json()
        gi = galaxy.GalaxyInstance(args.host, api_key)

    dataset_populator = GiDatasetPopulator(gi)
    workflow_populator = GiWorkflowPopulator(gi)
    cwl_populator = CwlPopulator(dataset_populator, workflow_populator)

    abs_cwd = os.path.abspath(args.cwd)

    tool = args.tool
    if not os.path.isabs(tool):
        tool = os.path.join(abs_cwd, tool)

    job = args.job
    if not os.path.isabs(job):
        job = os.path.join(abs_cwd, job)

    run = cwl_populator.run_cwl_job(tool, job)

    outputs = get_outputs(tool)
    output_names = [o.get_id() for o in outputs]
    outputs = collect_outputs(run, output_names, outdir=args.outdir)
    print(json.dumps(outputs, indent=4))
    # for output_dataset in output_datasets.values():
    #     name = output_dataset.name
    #     print(run.get_output_as_object(name))


if __name__ == "__main__":
    main()
