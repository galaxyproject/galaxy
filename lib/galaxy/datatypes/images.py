"""
Image classes
"""

import data
import logging
from galaxy.datatypes.binary import Binary
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes import metadata
from galaxy.datatypes.sniff import *
from galaxy.datatypes.util.image_util import *
from urllib import urlencode, quote_plus
import zipfile
import os, subprocess, tempfile, imghdr

try:
    import Image as PIL
except ImportError:
    try:
        from PIL import Image as PIL
    except:
        PIL = None

log = logging.getLogger(__name__)

# TODO: Uploading image files of various types is supported in Galaxy, but on
# the main public instance, the display_in_upload is not set for these data
# types in datatypes_conf.xml because we do not allow image files to be uploaded
# there.  There is currently no API feature that allows uploading files outside
# of a data library ( where it requires either the upload_paths or upload_directory
# option to be enabled, which is not the case on the main public instance ).  Because
# of this, we're currently safe, but when the api is enhanced to allow other uploads,
# we need to ensure that the implementation is such that image files cannot be uploaded
# to our main public instance.


class Image( data.Data ):
    """Class describing an image"""
    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek = 'Image in %s format' % dataset.extension
            dataset.blurb = data.nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
    def sniff( self, filename ):
        # First check if we can  use PIL
        if PIL is not None:
            try:
                im = PIL.open( filename )
                im.close()
                return True
            except:
                return False
        else:
            if imghdr.what( filename ) is not None:
                return True
            else:
                return False


class Jpg( Image ):
    file_ext = "jpeg"

    def sniff(self, filename, image=None):
        """Determine if the file is in jpg format."""
        return check_image_type( filename, ['JPEG'], image )


class Png( Image ):
    file_ext = "png"

    def sniff(self, filename, image=None):
        """Determine if the file is in png format."""
        return check_image_type( filename, ['PNG'], image )


class Tiff( Image ):
    file_ext = "tiff"

    def sniff(self, filename, image=None):
        """Determine if the file is in tiff format."""
        return check_image_type( filename, ['TIFF'], image )


class Bmp( Image ):
    file_ext = "bmp"

    def sniff(self, filename, image=None):
        """Determine if the file is in bmp format."""
        return check_image_type( filename, ['BMP'], image )


class Gif( Image ):
    file_ext = "gif"

    def sniff(self, filename, image=None):
        """Determine if the file is in gif format."""
        return check_image_type( filename, ['GIF'], image )


class Im( Image ):
    file_ext = "im"

    def sniff(self, filename, image=None):
        """Determine if the file is in im format."""
        return check_image_type( filename, ['IM'], image )


class Pcd( Image ):
    file_ext = "pcd"

    def sniff(self, filename, image=None):
        """Determine if the file is in pcd format."""
        return check_image_type( filename, ['PCD'], image )


class Pcx( Image ):
    file_ext = "pcx"

    def sniff(self, filename, image=None):
        """Determine if the file is in pcx format."""
        return check_image_type( filename, ['PCX'], image )


class Ppm( Image ):
    file_ext = "ppm"

    def sniff(self, filename, image=None):
        """Determine if the file is in ppm format."""
        return check_image_type( filename, ['PPM'], image )


class Psd( Image ):
    file_ext = "psd"

    def sniff(self, filename, image=None):
        """Determine if the file is in psd format."""
        return check_image_type( filename, ['PSD'], image )


class Xbm( Image ):
    file_ext = "xbm"

    def sniff(self, filename, image=None):
        """Determine if the file is in XBM format."""
        return check_image_type( filename, ['XBM'], image )


class Xpm( Image ):
    file_ext = "xpm"

    def sniff(self, filename, image=None):
        """Determine if the file is in XPM format."""
        return check_image_type( filename, ['XPM'], image )


class Rgb( Image ):
    file_ext = "rgb"

    def sniff(self, filename, image=None):
        """Determine if the file is in RGB format."""
        return check_image_type( filename, ['RGB'], image )


class Pbm( Image ):
    file_ext = "pbm"

    def sniff(self, filename, image=None):
        """Determine if the file is in PBM format"""
        return check_image_type( filename, ['PBM'], image )


class Pgm( Image ):
    file_ext = "pgm"

    def sniff(self, filename, image=None):
        """Determine if the file is in PGM format"""
        return check_image_type( filename, ['PGM'], image )


class Eps( Image ):
    file_ext = "eps"

    def sniff(self, filename, image=None):
        """Determine if the file is in eps format."""
        return check_image_type( filename, ['EPS'], image )


class Rast( Image ):
    file_ext = "rast"

    def sniff(self, filename, image=None):
        """Determine if the file is in rast format"""
        return check_image_type( filename, ['RAST'], image )


class Pdf( Image ):
    file_ext = "pdf"

    def sniff(self, filename):
        """Determine if the file is in pdf format."""
        headers = get_headers(filename, None, 1)
        try:
            if headers[0][0].startswith("%PDF"):
                return True
            else:
                return False
        except IndexError:
            return False

Binary.register_sniffable_binary_format("pdf", "pdf", Pdf)

def create_applet_tag_peek( class_name, archive, params ):
    text = """
<object classid="java:%s"
      type="application/x-java-applet"
      height="30" width="200" align="center" >
      <param name="archive" value="%s"/>""" % ( class_name, archive )
    for name, value in params.iteritems():
        text += """<param name="%s" value="%s"/>""" % ( name, value )
    text += """
<object classid="clsid:8AD9C840-044E-11D1-B3E9-00805F499D93"
        height="30" width="200" >
        <param name="code" value="%s" />
        <param name="archive" value="%s"/>""" % ( class_name, archive )
    for name, value in params.iteritems():
        text += """<param name="%s" value="%s"/>""" % ( name, value )
    text += """<div class="errormessage">You must install and enable Java in your browser in order to access this applet.<div></object>
</object>
"""
    return """<div><p align="center">%s</p></div>""" % text

class Gmaj( data.Data ):
    """Class describing a GMAJ Applet"""
    file_ext = "gmaj.zip"
    copy_safe_peek = False
    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            if hasattr( dataset, 'history_id' ):
                params = {
                "bundle":"display?id=%s&tofile=yes&toext=.zip" % dataset.id,
                "buttonlabel": "Launch GMAJ",
                "nobutton": "false",
                "urlpause" :"100",
                "debug": "false",
                "posturl": "history_add_to?%s" % "&".join( map( lambda x: "%s=%s" % ( x[0], quote_plus( str( x[1] ) ) ), [ ( 'copy_access_from', dataset.id), ( 'history_id', dataset.history_id ), ( 'ext', 'maf' ), ( 'name', 'GMAJ Output on data %s' % dataset.hid ), ( 'info', 'Added by GMAJ' ), ( 'dbkey', dataset.dbkey ) ] ) )
                }
                class_name = "edu.psu.bx.gmaj.MajApplet.class"
                archive = "/static/gmaj/gmaj.jar"
                dataset.peek = create_applet_tag_peek( class_name, archive, params )
                dataset.blurb = 'GMAJ Multiple Alignment Viewer'
            else:
                dataset.peek = "After you add this item to your history, you will be able to launch the GMAJ applet."
                dataset.blurb = 'GMAJ Multiple Alignment Viewer'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "peek unavailable"
    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'application/zip'
    def sniff(self, filename):
        """
        NOTE: the sniff.convert_newlines() call in the upload utility will keep Gmaj data types from being
        correctly sniffed, but the files can be uploaded (they'll be sniffed as 'txt').  This sniff function
        is here to provide an example of a sniffer for a zip file.
        """
        if not zipfile.is_zipfile( filename ):
            return False
        contains_gmaj_file = False
        zip_file = zipfile.ZipFile(filename, "r")
        for name in zip_file.namelist():
            if name.split(".")[1].strip().lower() == 'gmaj':
                contains_gmaj_file = True
                break
        zip_file.close()
        if not contains_gmaj_file:
            return False
        return True

class Html( data.Text ):
    """Class describing an html file"""
    file_ext = "html"

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek = "HTML file"
            dataset.blurb = data.nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'text/html'
    def sniff( self, filename ):
        """
        Determines whether the file is in html format

        >>> fname = get_test_fname( 'complete.bed' )
        >>> Html().sniff( fname )
        False
        >>> fname = get_test_fname( 'file.html' )
        >>> Html().sniff( fname )
        True
        """
        headers = get_headers( filename, None )
        try:
            for i, hdr in enumerate(headers):
                if hdr and hdr[0].lower().find( '<html>' ) >=0:
                    return True
            return False
        except:
            return True

class Laj( data.Text ):
    """Class describing a LAJ Applet"""
    file_ext = "laj"
    copy_safe_peek = False

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            if hasattr( dataset, 'history_id' ):
                params = {
                "alignfile1": "display?id=%s" % dataset.id,
                "buttonlabel": "Launch LAJ",
                "title": "LAJ in Galaxy",
                "posturl": quote_plus( "history_add_to?%s" % "&".join( [ "%s=%s" % ( key, value ) for key, value in { 'history_id': dataset.history_id, 'ext': 'lav', 'name': 'LAJ Output', 'info': 'Added by LAJ', 'dbkey': dataset.dbkey, 'copy_access_from': dataset.id }.items() ] ) ),
                "noseq": "true"
                }
                class_name = "edu.psu.cse.bio.laj.LajApplet.class"
                archive = "/static/laj/laj.jar"
                dataset.peek = create_applet_tag_peek( class_name, archive, params )
            else:
                dataset.peek = "After you add this item to your history, you will be able to launch the LAJ applet."
                dataset.blurb = 'LAJ Multiple Alignment Viewer'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "peek unavailable"
