"""
GIS classes
"""

import os
import logging
import sys

from galaxy.datatypes import data
from galaxy.datatypes.metadata import MetadataElement


verbose = False
gal_Log = logging.getLogger(__name__)


# The base class for all GIS data
class GIS(data.Data):
    """
    base class to use for gis datatypes
    """

    def __init__(self, **kwd):
        data.Data.__init__(self, **kwd)

    def set_peek(self, dataset, is_multi_byte=False):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = 'GIS data'
            dataset.blurb = 'data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'data/GIS'


# The shapefile class
class Shapefile(GIS):
    """
    Shapefile data
    derived from Data - composite datatype elements
    stored in extra files path
    """
#    http://en.wikipedia.org/wiki/Shapefile

    MetadataElement(name="base_name", desc="base name for all transformed versions of this dataset", default="Shapefile", readonly=True, set_in_upload=True)

    composite_type = 'auto_primary_file'
    file_ext = "shp"
    allow_datatype_change = False

    def generate_primary_file(self, dataset=None):
        rval = ['<html><head><title>Shapefile Galaxy Composite Dataset </title></head><p/>']
        rval.append('<div>This composite dataset is composed of the following files:<p/><ul>')
        for composite_name, composite_file in self.get_composite_files(dataset=dataset).items():
            fn = composite_name
            opt_text = ''
            if composite_file.optional:
                opt_text = ' (optional)'
            if composite_file.get('description'):
                rval.append('<li><a href="%s" type="application/binary">%s (%s)</a>%s</li>' % (fn, fn, composite_file.get('description'), opt_text))
            else:
                rval.append('<li><a href="%s" type="application/binary">%s</a>%s</li>' % (fn, fn, opt_text))
        rval.append('</ul></div></html>')
        return "\n".join(rval)

    def regenerate_primary_file(self, dataset):
        """
        cannot do this until we are setting metadata
        """
        shp = dataset.extra_files_path
        flist = os.listdir(shp)
        rval = ['<html><head><title>Files for Composite Dataset %s</title></head><body><p/>Composite %s contains:<p/><ul>' % (dataset.name, dataset.name)]
        for i, fname in enumerate(flist):
            sfname = os.path.split(fname)[-1]
            f, e = os.path.splitext(fname)
            rval.append('<li><a href="%s">%s</a></li>' % (sfname, sfname))
        rval.append('</ul></body></html>')
        with open(dataset.file_name, 'w') as f:
            f.write("\n".join(rval))
            f.write('\n')

    def set_meta(self, dataset, **kwd):
        """

        """
        GIS.set_meta(self, dataset, **kwd)
        if not kwd.get('overwrite'):
            if verbose:
                gal_Log.debug('@@@ shapefile set_meta called with overwrite = False')
            return True
        try:
            shp = dataset.extra_files_path
        except Exception:
            if verbose:
                gal_Log.debug('@@@shapefile set_meta failed %s - dataset %s has no shp ?' % (sys.exc_info()[0], dataset.name))
            return False
        try:
            flist = os.listdir(shp)
        except Exception:
            if verbose:
                gal_Log.debug('@@@shapefile set_meta failed %s - dataset %s has no shp ?' % (sys.exc_info()[0], dataset.name))
            return False
        if len(flist) == 0:
            if verbose:
                gal_Log.debug('@@@shapefile set_meta failed - %s shp %s is empty?' % (dataset.name, shp))
            return False
        self.regenerate_primary_file(dataset)
        if not dataset.info:
            dataset.info = 'Galaxy genotype datatype object'
        if not dataset.blurb:
            dataset.blurb = 'Composite file - shapefile Galaxy toolkit'
        return True

    def __init__(self, **kwd):
        GIS.__init__(self, **kwd)
        self.add_composite_file('shapefile.shp', description='Geometry File', is_binary=True, optional=False)
        self.add_composite_file('shapefile.shx', description='Geometry index File', is_binary=True, optional=False)
        self.add_composite_file('shapefile.dbf', description='Database File', is_binary=True, optional=False)
#        self.add_composite_file('shapefile.prj', description='Coordinate system informations', is_binary=True, optional=True)
