#!/usr/bin/env python
import argparse
import os
import sys
import time
from typing import Any

from galaxy.navigation.tours import (
    get_tour_id_from_path,
    load_tour_from_path,
)
from galaxy.selenium import cli
from galaxy.selenium.context import GalaxySeleniumContext
from galaxy.selenium.stories import (
    link_latest,
    run_directory,
    Story,
    write_story,
)
from galaxy.selenium.stories.tours import StoryTourCallback
from galaxy.selenium.web_element_protocol import WebElementProtocol

DESCRIPTION = "Walk a Galaxy tour and write it up as a story of highlighted screenshots."
FAILURE_DOCUMENTATION = "## Tour Failed\n\nThe tour stopped after the step above."


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    args = _arg_parser().parse_args(argv)
    driver_wrapper = cli.DriverWrapper(args)
    try:
        story = dump_tour(driver_wrapper, args.tour, args.output)
    finally:
        driver_wrapper.finish()
    print(f"Wrote {story.output_directory}")


def dump_tour(context: GalaxySeleniumContext, tour_path: str, output: str) -> Story:
    """Walk the tour, writing its story into a fresh run directory under ``output``."""
    tour = load_tour_from_path(tour_path, resolve_components=False)
    tour_id = get_tour_id_from_path(tour_path)
    directory = run_directory(os.path.abspath(output), f"{tour_id}_")
    story = Story(tour.get("name") or tour_id, tour.get("description") or "", directory)
    context.story = story
    try:
        context.run_tour(tour_path, tour_callback=DumpTourCallback(context))
    except BaseException:
        write_story(story, failure_documentation=FAILURE_DOCUMENTATION)
        print(f"Tour failed, partial story in {story.output_directory}", file=sys.stderr)
        raise
    story.finalize()
    link_latest(story.output_directory)
    return story


class DumpTourCallback(StoryTourCallback):
    def handle_step(self, step: dict[str, Any], step_index: int, element: WebElementProtocol | None = None) -> None:
        # Let the page settle before capturing, and the highlight clear before the step's clicks.
        time.sleep(0.5)
        super().handle_step(step, step_index, element)
        time.sleep(0.5)


def _arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("tour", metavar="TOUR", help="tour to walk")
    parser.add_argument(
        "-o",
        "--output",
        default="tour_dumps",
        help="directory to write each run's story into; 'latest' links the newest",
    )
    parser = cli.add_selenium_arguments(parser)
    return parser


if __name__ == "__main__":
    main()
