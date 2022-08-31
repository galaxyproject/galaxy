#!/bin/env python3
#
# Build the amp-galaxy tarball for distribution
#
import argparse
import logging
import tempfile
from pathlib import Path
import shutil
import sys
import yaml
from datetime import datetime
import os
import subprocess
import time
import tarfile
import io
from lib.galaxy.version import VERSION
from amp.package import *


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', default=False, action='store_true', help="Turn on debugging")
    parser.add_argument('--package', default=False, action='store_true', help="build a package instead of installing")
    parser.add_argument('destdir', nargs="?", help="Output directory for the package or install")
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if args.debug else logging.INFO)

    # Building Galaxy is actually:
    #   * run the galaxy startup so it will build the client and install any deps
    #   * copy the source repository to a temporary directory
    #   * remove a ton of things that we don't want to either put in the package or on the filesystem
    sourcedir = Path(sys.path[0])
    logging.info("Building Galaxy environment")
    subprocess.run(['scripts/common_startup.sh'], check=True)

    with tempfile.TemporaryDirectory(prefix="galaxy-build-") as builddir:
        logging.info(f"Copying instance to {builddir}")
        subprocess.run(["cp", "-a", str(sourcedir) + "/.", builddir], check=True)
                
        # building galaxy is really just a matter of removing a bunch of things:  
        logging.info("Removing non-dist directories")
        for n in ('.git', '.venv', 'static/plugins', '.ci', '.circleci', '.coveragerc', '.gitattributes',
                  '.gitignore', '.k8s_ci.Dockerfile', '.github', 
                  # files we've renamed because they were doing github things our account cannot                  
                  '.ci.upstream', '.dockerignore', '.circleci.upstream', '.github.upstream',
                  # parts of galaxy we don't use
                  'test', 'test-data', 'contrib', 'display_applications', 'doc', 'hooks', 'tool-data', 'run_tests.sh',
                  # packaging system stuff
                  'amp_build.py', 'amp_config.default', 'amp_hook_config.py'
                  ):            
            logging.debug(f"Removing entry {n}")
            if Path(builddir, n).exists():
                if Path(builddir, n).is_dir():
                    shutil.rmtree(builddir + "/" + n, ignore_errors=True)
                else:
                    Path(builddir, n).unlink()

        for n in ('__pycache__', 'node_modules', '.cache'):
            logging.debug(f"Finding {n} directories")
            for p in sorted([str(x) for x in Path(builddir).glob(f"**/{n}") if x.is_dir()], key=len, reverse=True):
                logging.debug(f"Removing directory {p}")
                shutil.rmtree(p)

        # we also want to clean up any runtime-popluated things
        for n in ('logs', 'database'):
            logging.debug(f"Clearing runtime {n}")
            shutil.rmtree(builddir + "/" + n, ignore_errors=True)
            os.mkdir(builddir + "/" + n)
   
        # The tools directory has a bunch of tools we don't want to install
        # it's easier to list what we want to keep...
        tools_to_keep = ('cloud/', 'data_source/upload.', 'data_source/import.')
        tools_dir = Path(builddir, "tools")        
        tool_dirs = set()
        for tfile in tools_dir.glob("**/*"):
            tfilename = tfile.relative_to(tools_dir)
            if tfile.is_dir():
                tool_dirs.add(tfile)
            for t in tools_to_keep:
                if str(tfilename).startswith(t):
                    logging.debug(f"Keeping tool file: {tfilename!s}")
                    break
            else:
                logging.debug(f"Removing tool file {tfilename!s}")
                if not tfile.is_dir():
                    tfile.unlink()
        for tooldir in sorted(tool_dirs, reverse=True):
            if len(list(tooldir.iterdir())) == 0:
                logging.debug(f"Removing empty tool dir: {tooldir!s}")
                tooldir.rmdir()



        if not args.package:
            # Installing the software
            # Effectively, we can just copy the contents of our build directory to the 
            # installation directory.  This won't copy the configuration bits used
            # by amp_control.py, so during development someone would copy them manually
            # and when a package is built it will get pulled then.        
            logging.info(f"Copying built instance to {args.destdir}")
            subprocess.run(["cp", "-a", f"{builddir}/." ,args.destdir], check=True)
        else:
            # Create the package
            try:
                new_package = create_package(Path(args.destdir), 
                                             Path(builddir),
                                             metadata={'name': 'galaxy', 
                                                       'version': VERSION, 
                                                       'install_path': 'galaxy'},
                                             hooks={'config': 'amp_hook_config.py'},
                                             defaults=Path("amp_config.default"))                                            
                logging.info(f"New package in {new_package}")    
            except Exception as e:
                logging.error(f"Failed to build backage: {e}")
                exit(1)


if __name__ == "__main__":
    main()
