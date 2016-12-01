#!/usr/bin/env python
import argparse
import datetime
import os
import time
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'test')))

from galaxy_selenium import cli

DESCRIPTION = "Walk a Galaxy tour and dump screenshots."


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    args = _arg_parser().parse_args(argv)
    driver_wrapper = cli.DriverWrapper(args)
    output = args.output
    assert output is not None
    output = output.replace("TIMESTAMP", datetime.datetime.now().strftime("%Y%m%d%H%M%s"))
    if os.path.exists(output):
        raise Exception("Output directory %s exists, skipping")
    else:
        os.makedirs(output)
    callback = DumpTourCallback(driver_wrapper, output)
    driver_wrapper.run_tour(args.tour, tour_callback=callback)


class DumpTourCallback(object):

    def __init__(self, driver_wrapper, output):
        self.driver_wrapper = driver_wrapper
        self.output = output

    def handle_step(self, step, step_index):
        time.sleep(.5)
        self.driver_wrapper.driver.save_screenshot("%s/%i.png" % (self.output, step_index))
        time.sleep(.5)


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('tour', metavar='TOUR', help='tour to walk')
    parser.add_argument('-o', '--output', default="tour_dump_TIMESTAMP", help='directory to dump tour to')
    parser = cli.add_selenium_arguments(parser)
    return parser


if __name__ == "__main__":
    main()
