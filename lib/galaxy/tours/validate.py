import argparse
import sys

import yaml
from pydantic import ValidationError

from galaxy.navigation.data import load_root_component
from ._impl import (
    get_tour_id_from_path,
    load_tour_from_path,
    tour_paths,
)
from ._schema import TourDetails

DESCRIPTION = "Perform static validation of a tour."


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    args = _arg_parser().parse_args(argv)
    target = args.target
    validated = True
    for tour_path in tour_paths(target):
        tour_id = get_tour_id_from_path(tour_path)

        def warn(msg):
            print(f"Tour '{tour_id}' warning: {msg}")  # noqa: B023

        message = None
        tour = None
        try:
            tour = load_tour_from_path(tour_path, warn=warn, resolve_components=False)
        except OSError:
            message = f"Tour '{tour_id}' could not be loaded, error reading file."
        except yaml.error.YAMLError:
            message = f"Tour '{tour_id}' could not be loaded, error within file. Please check your YAML syntax."
        except TypeError:
            message = (
                f"Tour '{tour_id}' could not be loaded, error within file."
                " Possibly spacing related. Please check your YAML syntax."
            )
        if tour:
            try:
                TourDetails(**tour)
            except ValidationError as e:
                message = f"Validation issue with tour data for '{tour_id}'. [{e}]"

            for tour_step in tour["steps"]:
                root_component = load_root_component()
                if "component" in tour_step:
                    component = tour_step["component"]
                    try:
                        root_component.resolve_component_locator(component)
                    except Exception as e:
                        message = f"Tour '{tour_id}' - failed to resolve component {component}. [{e}]"
        if message:
            validated = False
            print(message)
        else:
            print(f"Tour {tour_id} statically validated!")
    if not validated:
        raise ValueError("One or more tours failed static validation.")


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "target",
        metavar="TARGET",
        nargs="?",
        help="tour or directories of tours to validate",
        default="config/plugins/tours",
    )
    return parser


if __name__ == "__main__":
    main()
