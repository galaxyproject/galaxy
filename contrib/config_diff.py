#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Jelle Scholtalbers <j.scholtalbers@gmail.com>
Description:
  This script generates a tabular diff between two given ini files. The original purpose being to find
  new options in the galaxy.ini.sample file that are not yet in the users galaxy.ini file.
  Optionally, the output can be send to file and sorted.
"""

import logging
from operator import attrgetter

import click
import re
from six import iteritems

logger = logging.getLogger(__name__)

@click.command()
@click.option("--sort-key", "sort_keys", type=click.Choice(["diff", "active", "section", "option", "value", "comment"]), default=["section", "diff"], multiple=True, help="Multiple sort-key arguments can be given.")
@click.option("--hide-common-fields/--show-common-fields", default=True, help="Show all available options or only show options that are present in only one of the file (default).")
@click.option("--show-comment/--hide-comment", default=False, help="Hide (default) or show the comment field in the output.")
@click.argument("config_1", type=click.File("r"), metavar="<our.ini>")
@click.argument("config_2", type=click.File("r"), metavar="<their.ini>")
@click.argument("output", type=click.File("w"), default="-", metavar="<out.txt>")
def generate_diff(config_1, config_2, output, sort_keys, hide_common_fields, show_comment):
    """
    This script generates a diff between the two given .ini files. Optionally, the output can be send to file and sorted.

    Usage examples:

    \b
      python scripts/config_diff.py config/galaxy.ini config/galaxy.ini.sample --sort-key diff --sort-key active
      python scripts/config_diff.py --sort-key option --show-common-fields config/galaxy.ini config/galaxy.ini.sample galaxy.ini.diff
    """

    config_1_options = get_options(config_1)
    config_2_options = get_options(config_2)
    all_options = []

    for option_identifier, option_dict in iteritems(config_2_options):
        diff = "theirs"
        active = "NA"
        our_value = "NA"
        their_value = option_dict["value"]
        section = option_dict["section"]
        comment = option_dict["comment"]
        if option_identifier in config_1_options:
            active = config_1_options[option_identifier]["active"]
            our_value = config_1_options[option_identifier]["value"]
            diff = "both"
        all_options.append(Option(option_dict["option"], section, diff, active, our_value, their_value, comment))

    for option_identifier, option_dict in iteritems(config_1_options):
        if option_identifier not in config_2_options:
            all_options.append(
                Option(option_dict["option"], option_dict["section"], "ours", option_dict["active"], option_dict["value"], "NA",
                       option_dict["comment"]))

    outline = "Diff\tActive\tSection\tOption\tOur value\tTheir value\n"
    output_format = "{diff}\t{active}\t{section}\t{option}\t{our_value}\t{their_value}\n"
    if show_comment:
        outline = "Diff\tActive\tSection\tOption\tOur value\tTheir value\tComment\n"
        output_format = "{diff}\t{active}\t{section}\t{option}\t{our_value}\t{their_value}\t{comment}\n"

    output.write(outline)
    sorted_output = sorted(all_options, key=attrgetter(*sort_keys))
    for option in sorted_output:
        if not hide_common_fields or option.diff != "both":
            output.write(output_format.format(**option.as_dict()))


def get_options(config):
    config_options = {}
    current_section = None
    last_comment = ""
    prev_comment = ""
    for line in config:
        option_match = re.search('^(#*)(\w+)\s*=\s*(.+)$', line)
        section_match = re.match('^\[(.+)\]$', line)
        comment_match = re.match('^#\s(.+?)\s*$', line)
        if option_match:
            option_name = option_match.group(2)
            option_identifier = current_section + option_name
            config_options[option_identifier] = {
                "option": option_name,
                "active": "False" if option_match.group(1) == "#" else "True",
                "value": option_match.group(3),
                "section": current_section,
                "comment": last_comment if last_comment else prev_comment,
            }
            prev_comment = last_comment
            last_comment = ""

        elif section_match:
            current_section = section_match.group(1)
            last_comment = ""
        elif comment_match:
            if last_comment:
                last_comment += " " # add whitespace
            last_comment += comment_match.group(1)
    return config_options


class Option(object):
    def __init__(self, option, section, diff, active, our_value, their_value, comment):
        self.option = option
        self.section = section
        self.diff = diff
        self.active = active
        self.our_value = our_value
        self.their_value = their_value
        self.comment = comment

    def as_dict(self):
        return {
            "option": self.option,
            "section": self.section,
            "diff": self.diff,
            "active": self.active,
            "our_value": self.our_value,
            "their_value": self.their_value,
            "comment": self.comment}

if __name__ == "__main__":
    generate_diff()

