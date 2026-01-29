#!/usr/bin/env python
"""A small script to drive workflow performance testing.

% ./test/manual/launch_and_run.sh workflows_scaling --collection_size 500 --workflow_depth 4
$ .venv/bin/python scripts/summarize_timings.py --file /tmp/<work_dir>/handler1.log --pattern 'Workflow step'
$ .venv/bin/python scripts/summarize_timings.py --file /tmp/<work_dir>/handler1.log --pattern 'Created step'
"""
import functools
import json
import os
import random
import sys
from argparse import ArgumentParser
from threading import Thread
from uuid import uuid4

from bioblend import galaxy
from gxformat2 import python_to_workflow

galaxy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir))
sys.path[1:1] = [os.path.join(galaxy_root, "lib"), os.path.join(galaxy_root, "test")]

from galaxy_test.base.populators import (
    GiDatasetCollectionPopulator,
    GiDatasetPopulator,
    GiWorkflowPopulator,
)

LONG_TIMEOUT = 1000000000
DESCRIPTION = "Script to exercise the workflow engine."


def main(argv=None):
    """Entry point for workflow driving."""
    arg_parser = ArgumentParser(description=DESCRIPTION)
    arg_parser.add_argument("--api_key", default="testmasterapikey")
    arg_parser.add_argument("--host", default="http://localhost:8080/")

    arg_parser.add_argument("--collection_size", type=int, default=20)

    arg_parser.add_argument("--schedule_only_test", default=False, action="store_true")
    arg_parser.add_argument("--workflow_depth", type=int, default=10)
    arg_parser.add_argument("--workflow_count", type=int, default=1)

    group = arg_parser.add_mutually_exclusive_group()
    group.add_argument("--two_outputs", default=False, action="store_true")
    group.add_argument("--wave_simple", default=False, action="store_true")

    args = arg_parser.parse_args(argv)

    uuid = str(uuid4())
    workflow_struct = _workflow_struct(args, uuid)

    has_input = any(s.get("type", "tool") == "input_collection" for s in workflow_struct)
    if not has_input:
        uuid = None

    gi = _gi(args)

    workflow = python_to_workflow(workflow_struct)
    workflow_info = gi.workflows.import_workflow_json(workflow)
    workflow_id = workflow_info["id"]

    target = functools.partial(_run, args, gi, workflow_id, uuid)
    threads = []
    for _ in range(args.workflow_count):
        t = Thread(target=target)
        t.daemon = True
        t.start()
        threads.append(t)

    for t in threads:
        t.join()


def _run(args, gi, workflow_id, uuid):
    dataset_populator = GiDatasetPopulator(gi)
    dataset_collection_populator = GiDatasetCollectionPopulator(gi)

    history_id = dataset_populator.new_history()
    if uuid is not None:
        contents = []
        for i in range(args.collection_size):
            contents.append(f"random dataset number #{i}")
        hdca = dataset_collection_populator.create_list_in_history(history_id, contents=contents).json()
        label_map = {
            uuid: {"src": "hdca", "id": hdca["id"]},
        }
    else:
        label_map = {}

    workflow_request = dict(
        history=f"hist_id={history_id}",
    )
    workflow_request["inputs"] = json.dumps(label_map)
    url = f"workflows/{workflow_id}/usage"
    invoke_response = dataset_populator._post(url, data=workflow_request).json()
    invocation_id = invoke_response["id"]
    workflow_populator = GiWorkflowPopulator(gi)
    if args.schedule_only_test:
        workflow_populator.wait_for_invocation(
            workflow_id,
            invocation_id,
            timeout=LONG_TIMEOUT,
        )
    else:
        workflow_populator.wait_for_workflow(
            workflow_id,
            invocation_id,
            history_id,
            timeout=LONG_TIMEOUT,
        )


def _workflow_struct(args, input_uuid):
    if args.two_outputs:
        return _workflow_struct_two_outputs(args, input_uuid)
    elif args.wave_simple:
        return _workflow_struct_wave(args, input_uuid)
    else:
        return _workflow_struct_simple(args, input_uuid)


def _workflow_struct_simple(args, input_uuid):
    workflow_struct = [
        {"tool_id": "create_input_collection", "state": {"collection_size": args.collection_size}},
        {"tool_id": "cat", "state": {"input1": _link(0, "output")}},
    ]

    workflow_depth = args.workflow_depth
    for i in range(workflow_depth):
        link = str(i + 1) + "#out_file1"
        workflow_struct.append({"tool_id": "cat", "state": {"input1": _link(link)}})
    return workflow_struct


def _workflow_struct_two_outputs(args, input_uuid):
    workflow_struct = [
        {"type": "input_collection", "uuid": input_uuid},
        {"tool_id": "cat", "state": {"input1": _link(0), "input2": _link(0)}},
    ]

    workflow_depth = args.workflow_depth
    for i in range(workflow_depth):
        link1 = str(i + 1) + "#out_file1"
        link2 = str(i + 1) + "#out_file2"
        workflow_struct.append({"tool_id": "cat", "state": {"input1": _link(link1), "input2": _link(link2)}})
    return workflow_struct


def _workflow_struct_wave(args, input_uuid):
    workflow_struct = [
        {"tool_id": "create_input_collection", "state": {"collection_size": args.collection_size}},
        {"tool_id": "cat_list", "state": {"input1": _link(0, "output")}},
    ]

    workflow_depth = args.workflow_depth
    for i in range(workflow_depth):
        step = i + 2
        if step % 2 == 1:
            workflow_struct += [{"tool_id": "cat_list", "state": {"input1": _link(step - 1, "output")}}]
        else:
            workflow_struct += [{"tool_id": "split", "state": {"input1": _link(step - 1, "out_file1")}}]
    return workflow_struct


def _link(link, output_name=None):
    if output_name is not None:
        link = str(link) + "#" + output_name
    return {"$link": link}


def _gi(args):
    gi = galaxy.GalaxyInstance(args.host, key=args.api_key)
    name = f"wftest-user-{random.randint(0, 1000000)}"

    user = gi.users.create_local_user(name, f"{name}@galaxytesting.dev", "pass123")
    user_id = user["id"]
    api_key = gi.users.create_user_apikey(user_id)
    user_gi = galaxy.GalaxyInstance(args.host, api_key)
    return user_gi


if __name__ == "__main__":
    main()
