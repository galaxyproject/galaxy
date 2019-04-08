"""
GIS classes
"""

import logging
import os

from galaxy.datatypes import data
from galaxy.datatypes.metadata import MetadataElement


verbose = False
gal_Log = logging.getLogger(__name__)


# The base class for all GIS data
class GIS(data.Data):
    """
    base class to use for gis datatypes
    """

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

    MetadataElement(name="base_name", desc="base name for all transformed versions of this dataset", default="Shapefile", readonly=True, set_in_upload=True, optional=True)

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
            sfname = os.path.basename(fname)
            f, e = os.path.splitext(fname)
            rval.append('<li><a href="%s">%s</a></li>' % (sfname, sfname))
        rval.append('</ul></body></html>')
        with open(dataset.file_name, 'w') as f:
            f.write("\n".join(rval))
            f.write('\n')

    def set_meta(self, dataset, overwrite=True, **kwd):
        """

        """
        GIS.set_meta(self, dataset, **kwd)
        if not overwrite:
            if verbose:
                gal_Log.debug('@@@ shapefile set_meta called with overwrite = False')
            return True
        shp = dataset.extra_files_path
        flist = os.listdir(shp)
        if len(flist) == 0:
            if verbose:
                gal_Log.debug('@@@shapefile set_meta failed - %s shp %s is empty?' % (dataset.name, shp))
            raise Exception('@@@shapefile set_meta failed - %s shp %s is empty?' % (dataset.name, shp))
            return False
        self.regenerate_primary_file(dataset)
        return True

    def set_peek(self, dataset, is_multi_byte=False):
        """Set the peek and blurb text."""
        if not dataset.dataset.purged:
            dataset.peek = "Shapefile data"
            dataset.blurb = "Shapefile data"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        """Create HTML content, used for displaying peek."""
        try:
            return dataset.peek
        except Exception:
            return "Shapefile data"

    def __init__(self, **kwd):
        GIS.__init__(self, **kwd)
        self.add_composite_file('shapefile.shp', description='Geometry File .shp', is_binary=True, optional=False)
        self.add_composite_file('shapefile.shx', description='Geometry index File .shx', is_binary=True, optional=False)
        self.add_composite_file('shapefile.dbf', description='Database File .dbf', is_binary=True, optional=False)
#        self.add_composite_file('shapefile.sbn', description='Spatial index of the features .sbn', is_binary=True, optional=True)
#        self.add_composite_file('shapefile.sbx', description='Spatial index of the features .sbx', is_binary=True, optional=True)
#        self.add_composite_file('shapefile.fbn', description='Spatial index of the features that are read-only .fbn', is_binary=True, optional=True)
#        self.add_composite_file('shapefile.fbx', description='Spatial index of the features that are read-only .fbx', is_binary=True, optional=True)
#        self.add_composite_file('shapefile.ain', description='Attribute index .ain', is_binary=True, optional=True)
#        self.add_composite_file('shapefile.aih', description='Attribute index .aih', is_binary=True, optional=True)
#        self.add_composite_file('shapefile.atx', description='Attribute index for the dbf file .atx', is_binary=True, optional=True)
#        self.add_composite_file('shapefile.ixs', description='Geocoding index .ixs', is_binary=True, optional=True)
#        self.add_composite_file('shapefile.mxs', description='Geocoding index (ODB format) .mxs', is_binary=True, optional=True)
#        self.add_composite_file('shapefile.prj', description='Projection description .prj', is_binary=True, optional=True)
#        self.add_composite_file('shapefile.xml', description='Geospatial metadata .xml', is_binary=False, optional=True)
