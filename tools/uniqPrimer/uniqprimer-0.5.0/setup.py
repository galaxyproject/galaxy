from distutils.core import setup
import distutils.command.install
import os

class create_link(distutils.core.Command):
    
    def run( self ):
        #create a sym link to uniqprimer.py inside of /usr/local/bin
       os.symlink(  ) 
        

setup( name='uniqprimer',
       description='A Python tool for finding primers unique to a given genome',
       author='John Herndon',
       author_email='johnlherndon@gmail.com',
       version='0.5.0',
       packages=[ 'primertools' ],
       scripts=[ 'uniqprimer.py' ],
       data_files=[ ( '/usr/local/bin', [ 'uniqprimer.py' ] ) ] 
       
       )

