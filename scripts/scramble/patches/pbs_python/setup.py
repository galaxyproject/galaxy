#!/usr/bin/env python
#
# $Id: setup.py 434 2005-11-04 15:02:07Z bas $
#
# set ts=4
#

import sys
import os

from distutils.core import setup, Extension 

# Try some usefule defaults if not set
#
PBS_LIB_DIR='/opt/local/lib'
NEW_BUILD_SYSTEM=1

if not PBS_LIB_DIR:
	for dir in ['/usr/lib', '/usr/local/lib', '/opt/pbs/usr/lib', '/usr/lib/torque', '/opt/pbs/lib', '/opt/torque/lib' ]:
		dummy_new = os.path.join(dir, 'libtorque.so')
		dummy_old = os.path.join(dir, 'libpbs.a')
		if os.path.exists(dummy_new):
			PBS_LIB_DIR=dir
			break
		elif os.path.exists(dummy_old):
			PBS_LIB_DIR=dir
			NEW_BUILD_SYSTEM=0
			break

if not PBS_LIB_DIR:
	print 'Please specify where the PBS libraries are!!'
	print 'edit setup.py and fill in the PBS_LIB_DIR variable'
	sys.exit(1)

# Test if we have all the libs:
#
if NEW_BUILD_SYSTEM:
	LIBS = ['torque']
else:
	LIBS = ['log', 'net', 'pbs']
	for lib in LIBS:
		library = 'lib%s.a' %(lib)
		dummy = os.path.join(PBS_LIB_DIR, library)
    	if not os.path.exists(dummy):
			print 'You need to install "%s" in %s' %(library, PBS_LIB_DIR)
			sys.exit(1)

setup ( name = 'pbs_python',
	version = '2.9.4',
	description = 'openpbs/torque python interface',
	author = 'Bas van der Vlies',
	author_email = 'basv@sara.nl',
	url = 'http://www.sara.nl/index_eng.html',

	extra_path = 'pbs',
		package_dir = { '' : 'src' }, 
		py_modules = [ 'pbs', 'PBSQuery' ], 

	ext_modules = [ 
		Extension( '_pbs', ['src/pbs_wrap.c'],
		library_dirs = [ PBS_LIB_DIR ],
		libraries = LIBS) 
	]
)
