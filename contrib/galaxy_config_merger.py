#! /usr/bin/env python
"""
galaxy_config_merger.py

Created by Anne Pajon on 31 Jan 2012

Copyright (c) 2012 Cancer Research UK - Cambridge Research Institute.

Script for merging specific local Galaxy config galaxy.ini.cri with default Galaxy galaxy.ini.sample
"""

import configparser
import logging
import optparse
import sys


def main():
    # logging configuration
    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

    # get the options
    parser = optparse.OptionParser()
    parser.add_option("-s", "--sample", dest="sample", action="store", help="path to Galaxy galaxy.ini.sample file")
    parser.add_option("-c", "--config", dest="config", action="store", help="path to your own galaxy.ini file")
    parser.add_option(
        "-o", "--output", dest="output", action="store", help="path to the new merged galaxy.ini.new file"
    )
    (options, args) = parser.parse_args()

    for option in ["sample", "config"]:
        if getattr(options, option) is None:
            print(f"Please supply a --{option} parameter.\n")
            parser.print_help()
            sys.exit()

    config_sample = configparser.RawConfigParser()
    config_sample.read(options.sample)
    config_sample_content = open(options.sample).read()

    config = configparser.RawConfigParser()
    config.read(options.config)

    logging.info(f"Merging your own config file {options.config} into the sample one {options.sample}.")
    logging.info("---------- DIFFERENCE ANALYSIS BEGIN ----------")
    for section in config.sections():
        if not config_sample.has_section(section):
            logging.warning("-MISSING- section [%s] not found in sample file. It will be ignored.", section)
        else:
            for name, value in config.items(section):
                if not config_sample.has_option(section, name):
                    if f"#{name}" not in config_sample_content:
                        logging.warning(
                            f"-MISSING- section [{section}] option '{name}' not found in sample file. It will be ignored."
                        )
                    else:
                        logging.info(
                            f"-notset- section [{section}] option '{name}' not set in sample file. It will be added."
                        )
                        config_sample.set(section, name, value)
                else:
                    if not config_sample.get(section, name) == value:
                        logging.info(
                            f"- diff - section [{section}] option '{name}' has different value ('{config_sample.get(section, name)}':'{value}'). It will be modified."
                        )
                        config_sample.set(section, name, value)
    logging.info("---------- DIFFERENCE ANALYSIS END   ----------")

    if options.output:
        outputfile = open(options.output, "w")
        config_sample.write(outputfile)
        outputfile.close()
    else:
        logging.info("use -o OUTPUT to write the merged configuration into a file.")

    logging.info("read Galaxy galaxy.ini.sample for detailed information.")


if __name__ == "__main__":
    main()
