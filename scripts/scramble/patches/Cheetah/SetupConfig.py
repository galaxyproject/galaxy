#-------Main Package Settings-----------#
import sys

name = 'Cheetah'
from cheetah.Version import Version as version
maintainer = "R. Tyler Ballance"
author = "Tavis Rudd"
author_email = "cheetahtemplate-discuss@lists.sf.net"
url = "http://www.cheetahtemplate.org/"
packages = ['Cheetah',
            'Cheetah.Macros',            
            'Cheetah.Templates',
            'Cheetah.Tests',
            'Cheetah.Tools',
            'Cheetah.Utils',
            ]
classifiers = [line.strip() for line in '''\
  #Development Status :: 4 - Beta
  Development Status :: 5 - Production/Stable
  Intended Audience :: Developers
  Intended Audience :: System Administrators
  License :: OSI Approved :: MIT License
  Operating System :: OS Independent
  Programming Language :: Python
  Topic :: Internet :: WWW/HTTP
  Topic :: Internet :: WWW/HTTP :: Dynamic Content
  Topic :: Internet :: WWW/HTTP :: Site Management
  Topic :: Software Development :: Code Generators
  Topic :: Software Development :: Libraries :: Python Modules
  Topic :: Software Development :: User Interfaces
  Topic :: Text Processing'''.splitlines() if not line.strip().startswith('#')]
del line

package_dir = {'Cheetah':'cheetah'}

import os
import os.path
from distutils.core import Extension

ext_modules=[
             Extension("Cheetah._namemapper", 
                        [os.path.join('cheetah', 'c', '_namemapper.c')]),
           #  Extension("Cheetah._verifytype", 
           #             [os.path.join('cheetah', 'c', '_verifytype.c')]),
           #  Extension("Cheetah._filters", 
           #             [os.path.join('cheetah', 'c', '_filters.c')]),
           #  Extension('Cheetah._template',
           #             [os.path.join('cheetah', 'c', '_template.c')]),
             ]

## Data Files and Scripts
scripts = ['bin/cheetah-compile',
           'bin/cheetah',
           ]

data_files = ['recursive: cheetah *.tmpl *.txt LICENSE README TODO CHANGES',]

if not os.getenv('CHEETAH_INSTALL_WITHOUT_SETUPTOOLS'):
    try:
        from setuptools import setup
#        install_requires = [
#                "Markdown >= 2.0.1",
#        ]
        if sys.platform == 'win32':
            # use 'entry_points' instead of 'scripts'
            del scripts
            entry_points = {
                'console_scripts': [
                    'cheetah = Cheetah.CheetahWrapper:_cheetah',
                    'cheetah-compile = Cheetah.CheetahWrapper:_cheetah_compile',
                ]
        }
    except ImportError:
        print 'Not using setuptools, so we cannot install the Markdown dependency'


description = "Cheetah is a template engine and code generation tool."

long_description = '''Cheetah is an open source template engine and code generation tool.

It can be used standalone or combined with other tools and frameworks. Web
development is its principle use, but Cheetah is very flexible and is also being
used to generate C++ game code, Java, sql, form emails and even Python code.

Documentation
================================================================================
For a high-level introduction to Cheetah please refer to the User\'s Guide
at http://www.cheetahtemplate.org/learn.html

Mailing list
================================================================================
cheetahtemplate-discuss@lists.sourceforge.net
Subscribe at http://lists.sourceforge.net/lists/listinfo/cheetahtemplate-discuss

Credits
================================================================================
http://www.cheetahtemplate.org/credits.html

Recent Changes
================================================================================
See http://www.cheetahtemplate.org/CHANGES.txt for full details

'''
