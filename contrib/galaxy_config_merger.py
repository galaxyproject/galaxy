#! /usr/bin/env python
'''
galaxy_config_merger.py

Created by Anne Pajon on 31 Jan 2012

Copyright (c) 2012 Cancer Research UK - Cambridge Research Institute.

This source file is licensed under the Academic Free License version
3.0 available at http://www.opensource.org/licenses/AFL-3.0.

Permission is hereby granted to reproduce, translate, adapt, alter,
transform, modify, or arrange this source file (the "Original Work");
to distribute or communicate copies of it under any license of your
choice that does not contradict the terms and conditions; to perform
or display the Original Work publicly.

THE ORIGINAL WORK IS PROVIDED UNDER THIS LICENSE ON AN "AS IS" BASIS
AND WITHOUT WARRANTY, EITHER EXPRESS OR IMPLIED, INCLUDING, WITHOUT
LIMITATION, THE WARRANTIES OF NON-INFRINGEMENT, MERCHANTABILITY OR
FITNESS FOR A PARTICULAR PURPOSE. THE ENTIRE RISK AS TO THE QUALITY OF
THE ORIGINAL WORK IS WITH YOU.

Script for merging specific local Galaxy config galaxy.ini.cri with default Galaxy galaxy.ini.sample
'''
from __future__ import print_function

import logging
import optparse
import sys

from six.moves import configparser


def main():
    # logging configuration
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    # get the options
    parser = optparse.OptionParser()
    parser.add_option("-s", "--sample", dest="sample", action="store", help="path to Galaxy galaxy.ini.sample file")
    parser.add_option("-c", "--config", dest="config", action="store", help="path to your own galaxy.ini file")
    parser.add_option("-o", "--output", dest="output", action="store", help="path to the new merged galaxy.ini.new file")
    (options, args) = parser.parse_args()

    for option in ['sample', 'config']:
        if getattr(options, option) is None:
            print("Please supply a --%s parameter.\n" % (option))
            parser.print_help()
            sys.exit()

    config_sample = configparser.RawConfigParser()
    config_sample.read(options.sample)
    config_sample_content = open(options.sample, 'r').read()

    config = configparser.RawConfigParser()
    config.read(options.config)

    logging.info("Merging your own config file %s into the sample one %s." % (options.config, options.sample))
    logging.info("---------- DIFFERENCE ANALYSIS BEGIN ----------")
    for section in config.sections():
        if not config_sample.has_section(section):
            logging.warning("-MISSING- section [%s] not found in sample file. It will be ignored." % section)
        else:
            for (name, value) in config.items(section):
                if not config_sample.has_option(section, name):
                    if not "#%s" % name in config_sample_content:
                        logging.warning("-MISSING- section [%s] option '%s' not found in sample file. It will be ignored." % (section, name))
                    else:
                        logging.info("-notset- section [%s] option '%s' not set in sample file. It will be added." % (section, name))
                        config_sample.set(section, name, value)
                else:
                    if not config_sample.get(section, name) == value:
                        logging.info("- diff - section [%s] option '%s' has different value ('%s':'%s'). It will be modified." % (section, name, config_sample.get(section, name), value))
                        config_sample.set(section, name, value)
    logging.info("---------- DIFFERENCE ANALYSIS END   ----------")

    if options.output:
        outputfile = open(options.output, 'w')
        config_sample.write(outputfile)
        outputfile.close()
    else:
        # print "----------"
        # config_sample.write(sys.stdout)
        # print "----------"
        logging.info("use -o OUTPUT to write the merged configuration into a file.")

    logging.info("read Galaxy galaxy.ini.sample for detailed information.")


if __name__ == '__main__':
    main()
