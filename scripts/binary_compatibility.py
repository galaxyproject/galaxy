#!/usr/bin/env python
"""
Creates a Python binary-compatibility.cfg as described here:

    https://mail.python.org/pipermail/distutils-sig/2015-July/026617.html
"""
from __future__ import print_function

# Vaguely Python 2.6 compatibile ArgumentParser import
try:
    from argparse import ArgumentParser
except ImportError:
    from optparse import OptionParser

    class ArgumentParser(OptionParser):

        def __init__(self, **kwargs):
            self.delegate = OptionParser(**kwargs)

        def add_argument(self, *args, **kwargs):
            if "required" in kwargs:
                del kwargs["required"]
            return self.delegate.add_option(*args, **kwargs)

        def parse_args(self, args=None):
            (options, args) = self.delegate.parse_args(args)
            return options

import sys
import json

from pip.pep425tags import get_supported
from pip.platform import get_specific_platform


compatible_platforms = {
    'centos': 'rhel',
    'scientific': 'rhel',
}


def install_compat():
    spec_plat = get_specific_platform()
    if spec_plat is None:
        return None
    this_plat = spec_plat[0]
    compat_plat = compatible_platforms.get(this_plat, None)
    rval = {}
    if compat_plat:
        print('{0} is binary compatible with {1} (and can install {2} wheels)'
              .format(this_plat, compat_plat, compat_plat),
              file=sys.stderr)
        for py, abi, plat in get_supported():
            if this_plat in plat:
                rval[plat] = {'install': [plat.replace(this_plat, compat_plat)]}
    return rval


def main():
    arg_parser = ArgumentParser()
    arg_parser.add_argument('-o', '--output', default=None, help='Output to file')
    args = arg_parser.parse_args()

    compat = install_compat()

    if compat:
        if args.output is not None:
            with open(args.output, 'w') as out:
                json.dump(compat, out)
        else:
            print(json.dumps(install_compat()))


if __name__ == '__main__':
    main()
