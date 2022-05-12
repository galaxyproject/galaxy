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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', default=False, action='store_true', help="Turn on debugging")
    parser.add_argument('--version', default=None, help="Package Version")  
    parser.add_argument('--package', default=False, action='store_true', help="build a package instead of installing")
    parser.add_argument('destdir', nargs="?", help="Output directory for the package")
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if args.debug else logging.INFO)

    # force a download of the requirements and rebuild the client if necessary.
    logging.info("Building environment")
    subprocess.run(['scripts/common_startup.sh'], check=True)

    if not args.package:
        logging.info("Galaxy should be ready for use")
        exit(0)

    if not args.destdir:
        logging.error("A destination directory must be specified when creating a package")
        exit(1)

    



    # get our directories
    here = Path.cwd().resolve()
    destdir = Path(args.destdir).resolve()
    sourcedir = Path(sys.path[0]).resolve()

    with tempfile.TemporaryDirectory(prefix="galaxy-build-") as builddir:
        logging.info(f"Copying instance to {builddir}")
        subprocess.run(["cp", "-a", str(sourcedir) + "/.", builddir], check=True)
                
        # building galaxy is really just a matter of removing a bunch of things:  
        logging.info("Removing non-dist directories")
        for n in ('.git', '.venv', 'static/plugins', '.ci', '.circleci', '.coveragerc', '.gitattributes',
                  '.gitignore', '.k8s_ci.Dockerfile', '.github'):            
            logging.debug(f"Removing entry {n}")
            if Path(builddir, n).is_dir():
                shutil.rmtree(builddir + "/" + n, ignore_errors=True)
            else:
                Path(builddir, n).unlink(missing_ok=True)

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

        # build the package.
        buildtime = datetime.now().strftime("%Y%m%d_%H%M%S")        
        if args.version is None:
            args.version = VERSION

        logging.info(f"Creating amp_galaxy package for with version {args.version} in {destdir}")
        basedir= f"amp_galaxy-{args.version}"
        pkgfile = Path(destdir, f"{basedir}.tar")
        with tarfile.TarFile(pkgfile, "w") as tfile:
            # create base directory
            base_info = tarfile.TarInfo(name=basedir)
            base_info.mtime = int(time.time())
            base_info.type = tarfile.DIRTYPE
            base_info.mode = 0o755
            tfile.addfile(base_info, None)                    

            # write metadata file
            metafile = tarfile.TarInfo(name=f"{basedir}/amp_package.yaml")
            metafile_data = yaml.safe_dump({
                'name': 'amp_galaxy',
                'version': args.version,
                'build_date': buildtime,
                'install_path': 'galaxy'
            }).encode('utf-8')
            metafile.size = len(metafile_data)
            metafile.mtime = int(time.time())
            metafile.mode = 0o644
            tfile.addfile(metafile, io.BytesIO(metafile_data))
            logging.debug(f"Pushing data from {builddir!s} to data in tarball")
            tfile.add(builddir, f'{basedir}/data', recursive=True)
        
        logging.info(f"Package has been created {pkgfile!s}")

if __name__ == "__main__":
    main()
