from os import walk
from os.path import join
from setuptools import setup, find_packages

def walk_files( top ):
    for dir, dirs, files in walk( top ):
        yield( dir, [ join( dir, f ) for f in files ] )

setup(
        name = "GeneTrack",
        version = "2.0.0-beta-1",
        packages = ['genetrack','genetrack.scripts'],
        data_files = [ f for f in walk_files('tests') ],
        zip_safe = False
)
