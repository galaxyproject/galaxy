import os
import random
import sys
from argparse import ArgumentParser

from bioblend import galaxy

galaxy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir))
sys.path[1:1] = [os.path.join(galaxy_root, "lib"), os.path.join(galaxy_root, "test")]

from galaxy_test.base.populators import GiDatasetPopulator

DESCRIPTION = "Script to generate history export test artifacts."


def main(argv=None):
    arg_parser = ArgumentParser(description=DESCRIPTION)
    arg_parser.add_argument("--api_key", default="testmasterapikey")
    arg_parser.add_argument("--host", default="http://localhost:8080/")

    args = arg_parser.parse_args(argv)
    gi = _gi(args)

    _run(args, gi)


def _run(args, gi):
    dataset_populator = GiDatasetPopulator(gi)
    history_id = dataset_populator.new_history()
    input_hda = dataset_populator.new_dataset(history_id, content="1 2 3")
    deleted_hda = dataset_populator.new_dataset(history_id, content="1 2 3")
    dataset_populator.delete_dataset(history_id, deleted_hda["id"])
    inputs = {
        "input1": {"src": "hda", "id": input_hda["id"]},
        "queries_0|input2": {"src": "hda", "id": input_hda["id"]},
    }
    dataset_populator.run_tool("cat", inputs, history_id)
    dataset_populator.wait_for_history(history_id, assert_ok=True)

    # Export the history.
    export_kwds = {}
    export_url = dataset_populator.export_url(history_id, export_kwds)
    export_response = dataset_populator.get_export_url(export_url)
    with open("download.tar.gz", "wb") as f:
        f.write(export_response.content)


def _gi(args):
    gi = galaxy.GalaxyInstance(args.host, key=args.api_key)
    name = "histexport-user-%d" % random.randint(0, 1000000)

    user = gi.users.create_local_user(name, f"{name}@galaxytesting.dev", "pass123")
    user_id = user["id"]
    api_key = gi.users.create_user_apikey(user_id)
    user_gi = galaxy.GalaxyInstance(args.host, api_key)
    return user_gi


if __name__ == "__main__":
    main()
