# setup.py - distutils packaging
#
# Copyright (C) 2003-2004 Federico Di Gregorio  <fog@debian.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"""Python-PostgreSQL Database Adapter

psycopg is a PostgreSQL database adapter for the Python programming
language. This is version 2, a complete rewrite of the original code to
provide new-style classes for connection and cursor objects and other sweet
candies. Like the original, psycopg 2 was written with the aim of being
very small and fast, and stable as a rock.

psycopg is different from the other database adapter because it was
designed for heavily multi-threaded applications that create and destroy
lots of cursors and make a conspicuous number of concurrent INSERTs or
UPDATEs. psycopg 2 also provide full asycronous operations for the really
brave programmer.
"""

classifiers = """\
Development Status :: 4 - Beta
Intended Audience :: Developers
License :: OSI Approved :: GNU General Public License (GPL)
License :: OSI Approved :: Zope Public License
Programming Language :: Python
Programming Language :: C
Programming Language :: SQL
Topic :: Database
Topic :: Database :: Front-Ends
Topic :: Software Development
Topic :: Software Development :: Libraries :: Python Modules
Operating System :: Microsoft :: Windows
Operating System :: Unix
"""

import os
import os.path
import sys
import popen2
import ConfigParser
from glob import glob
from distutils.core import setup, Extension
from distutils.errors import DistutilsFileError
from distutils.command.build_ext import build_ext
from distutils.sysconfig import get_python_inc
from distutils.ccompiler import get_default_compiler

assert sys.version_info[:2] >= ( 2, 4 )

PSYCOPG_VERSION = '2.0.6'
version_flags   = []

PG_VERSION = '8.2.6'

class psycopg_build_ext(build_ext):
    """Conditionally complement the setup.cfg options file.

    This class configures the include_dirs, libray_dirs, libraries
    options as required by the system. Most of the configuration happens
    in finalize_options() method.

    If you want to set up the build step for a peculiar platform, add a
    method finalize_PLAT(), where PLAT matches your sys.platform.
    """
    user_options = build_ext.user_options[:]
    user_options.extend([
        ('use-pydatetime', None,
         "Use Python datatime objects for date and time representation."),
        ('use-decimal', None,
         "Use Decimal type even on Python 2.3 if the module is provided."),
    ])

    boolean_options = build_ext.boolean_options[:]
    boolean_options.extend(('use-pydatetime', 'use-decimal', 'have-ssl'))

    def initialize_options(self):
        build_ext.initialize_options(self)
        self.use_pg_dll = 1
        self.pgdir = None
        self.mx_include_dir = None

    def get_compiler(self):
        """Return the name of the C compiler used to compile extensions.

        If a compiler was not explicitely set (on the command line, for
        example), fall back on the default compiler.
        """
        if self.compiler:
            # distutils doesn't keep the type of self.compiler uniform; we
            # compensate:
            if isinstance(self.compiler, str):
                name = self.compiler
            else:
                name = self.compiler.compiler_type
        else:
            name = get_default_compiler()
        return name

    def finalize_darwin(self):
        """Finalize build system configuration on darwin platform."""
        self.libraries.append('ssl')
        self.libraries.append('crypto')

    def finalize_options(self):
        """Complete the build system configuation."""
        build_ext.finalize_options(self)

        self.include_dirs.append(".")
        self.include_dirs.append("postgresql-8.2.6/src/interfaces/libpq")
        self.include_dirs.append("postgresql-8.2.6/src/include")
        self.include_dirs.append("postgresql-8.2.6/src/port")
        pgmajor, pgminor, pgpatch = PG_VERSION.split('.')
        define_macros.append(("PG_MAJOR_VERSION", pgmajor))
        define_macros.append(("PG_MINOR_VERSION", pgminor))
        define_macros.append(("PG_PATCH_VERSION", pgpatch))

        if hasattr(self, "finalize_" + sys.platform):
            getattr(self, "finalize_" + sys.platform)()

# let's start with macro definitions (the ones not already in setup.cfg)
define_macros = []
include_dirs = []

# python version
define_macros.append(('PY_MAJOR_VERSION', str(sys.version_info[0])))
define_macros.append(('PY_MINOR_VERSION', str(sys.version_info[1])))

# some macros related to python versions and features
if sys.version_info[0] >= 2 and sys.version_info[1] >= 3:
    define_macros.append(('HAVE_PYBOOL','1'))

# gather information to build the extension module
ext = [] ; data_files = []

# sources

sources = [
    'psycopgmodule.c', 'pqpath.c',  'typecast.c',
    'microprotocols.c', 'microprotocols_proto.c',
    'connection_type.c', 'connection_int.c', 'cursor_type.c', 'cursor_int.c',
    'adapter_qstring.c', 'adapter_pboolean.c', 'adapter_binary.c',
    'adapter_asis.c', 'adapter_list.c']

parser = ConfigParser.ConfigParser()
parser.read('setup.cfg')

# Choose if to use Decimal type
use_decimal = int(parser.get('build_ext', 'use_decimal'))
if sys.version_info[0] >= 2 and (
    sys.version_info[1] >= 4 or (sys.version_info[1] == 3 and use_decimal)):
    define_macros.append(('HAVE_DECIMAL','1'))
    version_flags.append('dec')

# Choose a datetime module
have_pydatetime = False
have_mxdatetime = False
use_pydatetime  = int(parser.get('build_ext', 'use_pydatetime'))

# check for mx package
if parser.has_option('build_ext', 'mx_include_dir'):
    mxincludedir = parser.get('build_ext', 'mx_include_dir')
else:
    mxincludedir = os.path.join(get_python_inc(plat_specific=1), "mx")
if os.path.exists(mxincludedir):
    include_dirs.append(mxincludedir)
    define_macros.append(('HAVE_MXDATETIME','1'))
    sources.append('adapter_mxdatetime.c')
    have_mxdatetime = True
    version_flags.append('mx')

# check for python datetime package
if os.path.exists(os.path.join(get_python_inc(plat_specific=1),"datetime.h")):
    define_macros.append(('HAVE_PYDATETIME','1'))
    sources.append('adapter_datetime.c')
    have_pydatetime = True
    version_flags.append('dt')

# now decide which package will be the default for date/time typecasts
if have_pydatetime and use_pydatetime \
       or have_pydatetime and not have_mxdatetime:
    define_macros.append(('PSYCOPG_DEFAULT_PYDATETIME','1'))
elif have_mxdatetime:
    define_macros.append(('PSYCOPG_DEFAULT_MXDATETIME','1'))
else:
    def e(msg):
        sys.stderr.write("error: " + msg + "\n")
    e("psycopg requires a datetime module:")
    e("    mx.DateTime module not found")
    e("    python datetime module not found")
    e("Note that psycopg needs the module headers and not just the module")
    e("itself. If you installed Python or mx.DateTime from a binary package")
    e("you probably need to install its companion -dev or -devel package.")
    sys.exit(1)

# generate a nice version string to avoid confusion when users report bugs
for have in parser.get('build_ext', 'define').split(','):
    if have == 'PSYCOPG_EXTENSIONS':
        version_flags.append('ext')
    elif have == 'HAVE_PQPROTOCOL3':
        version_flags.append('pq3')
if version_flags:
    PSYCOPG_VERSION_EX = PSYCOPG_VERSION + " (%s)" % ' '.join(version_flags)
else:
    PSYCOPG_VERSION_EX = PSYCOPG_VERSION

define_macros.append(('PSYCOPG_VERSION', '"'+PSYCOPG_VERSION_EX+'"'))

if parser.has_option('build_ext', 'have_ssl'):
    have_ssl = int(parser.get('build_ext', 'have_ssl'))
else:
    have_ssl = 0

# build the extension

sources = map(lambda x: os.path.join('psycopg', x), sources)
sources.append( 'postgresql-%s/src/port/pgstrcasecmp.c' % PG_VERSION )
sources.append( 'postgresql-%s/src/backend/libpq/md5.c' % PG_VERSION )
sources.extend( glob('postgresql-%s/src/interfaces/libpq/*.c' % PG_VERSION) )

ext.append(Extension("psycopg2._psycopg", sources,
                     define_macros=define_macros,
                     include_dirs=include_dirs,
                     undef_macros=[]))
setup(name="psycopg2",
      version=PSYCOPG_VERSION,
      maintainer="Federico Di Gregorio",
      maintainer_email="fog@initd.org",
      author="Federico Di Gregorio",
      author_email="fog@initd.org",
      url="http://initd.org/tracker/psycopg",
      download_url = "http://initd.org/pub/software/psycopg2",
      license="GPL with exceptions or ZPL",
      platforms = ["any"],
      description=__doc__.split("\n")[0],
      long_description="\n".join(__doc__.split("\n")[2:]),
      classifiers=filter(None, classifiers.split("\n")),
      data_files=data_files,
      package_dir={'psycopg2':'lib'},
      packages=['psycopg2'],
      cmdclass={ 'build_ext': psycopg_build_ext },
      ext_modules=ext)

