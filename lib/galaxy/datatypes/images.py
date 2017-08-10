"""
Image classes
"""
import logging
import zipfile

from six.moves.urllib.parse import quote_plus

from galaxy.datatypes.binary import Binary
from galaxy.datatypes.sniff import get_headers
from galaxy.datatypes.text import Html as HtmlFromText
from galaxy.util import nice_size
from galaxy.util.image_util import check_image_type
from . import data

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
    edam_data = 'data_2968'
    edam_format = "format_3547"
    file_ext = ''

    def __init__(self, **kwd):
        super(Image, self).__init__(**kwd)
        self.image_formats = [self.file_ext.upper()]

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek = 'Image in %s format' % dataset.extension
            dataset.blurb = nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def sniff( self, filename ):
        """Determine if the file is in this format"""
        return check_image_type( filename, self.image_formats )


class Jpg( Image ):
    edam_format = "format_3579"
    file_ext = "jpg"

    def __init__(self, **kwd):
        super(Jpg, self).__init__(**kwd)
        self.image_formats = ['JPEG']


class Png( Image ):
    edam_format = "format_3603"
    file_ext = "png"


class Tiff( Image ):
    edam_format = "format_3591"
    file_ext = "tiff"


class Hamamatsu( Image ):
    file_ext = "vms"


class Mirax( Image ):
    file_ext = "mrxs"


class Sakura( Image ):
    file_ext = "svslide"


class Nrrd( Image ):
    file_ext = "nrrd"


class Bmp( Image ):
    edam_format = "format_3592"
    file_ext = "bmp"


class Gif( Image ):
    edam_format = "format_3467"
    file_ext = "gif"


class Im( Image ):
    edam_format = "format_3593"
    file_ext = "im"


class Pcd( Image ):
    edam_format = "format_3594"
    file_ext = "pcd"


class Pcx( Image ):
    edam_format = "format_3595"
    file_ext = "pcx"


class Ppm( Image ):
    edam_format = "format_3596"
    file_ext = "ppm"


class Psd( Image ):
    edam_format = "format_3597"
    file_ext = "psd"


class Xbm( Image ):
    edam_format = "format_3598"
    file_ext = "xbm"


class Xpm( Image ):
    edam_format = "format_3599"
    file_ext = "xpm"


class Rgb( Image ):
    edam_format = "format_3600"
    file_ext = "rgb"


class Pbm( Image ):
    edam_format = "format_3601"
    file_ext = "pbm"


class Pgm( Image ):
    edam_format = "format_3602"
    file_ext = "pgm"


class Eps( Image ):
    edam_format = "format_3466"
    file_ext = "eps"


class Rast( Image ):
    edam_format = "format_3605"
    file_ext = "rast"


class Pdf( Image ):
    edam_format = "format_3508"
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
    for name, value in params.items():
        text += """<param name="%s" value="%s"/>""" % ( name, value )
    text += """
<object classid="clsid:8AD9C840-044E-11D1-B3E9-00805F499D93"
        height="30" width="200" >
        <param name="code" value="%s" />
        <param name="archive" value="%s"/>""" % ( class_name, archive )
    for name, value in params.items():
        text += """<param name="%s" value="%s"/>""" % ( name, value )
    text += """<div class="errormessage">You must install and enable Java in your browser in order to access this applet.<div></object>
</object>
"""
    return """<div><p align="center">%s</p></div>""" % text


class Gmaj( data.Data ):
    """Class describing a GMAJ Applet"""
    edam_format = "format_3547"
    file_ext = "gmaj.zip"
    copy_safe_peek = False

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            if hasattr( dataset, 'history_id' ):
                params = {
                    "bundle": "display?id=%s&tofile=yes&toext=.zip" % dataset.id,
                    "buttonlabel": "Launch GMAJ",
                    "nobutton": "false",
                    "urlpause": "100",
                    "debug": "false",
                    "posturl": "history_add_to?%s" % "&".join( "%s=%s" % ( x[0], quote_plus( str( x[1] ) ) ) for x in [ ( 'copy_access_from', dataset.id), ( 'history_id', dataset.history_id ), ( 'ext', 'maf' ), ( 'name', 'GMAJ Output on data %s' % dataset.hid ), ( 'info', 'Added by GMAJ' ), ( 'dbkey', dataset.dbkey ) ] )
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


class Html( HtmlFromText ):
    """Deprecated class. This class should not be used anymore, but the galaxy.datatypes.text:Html one.
    This is for backwards compatibilities only."""


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
                    "posturl": quote_plus( "history_add_to?%s" % "&".join( "%s=%s" % ( key, value ) for key, value in { 'history_id': dataset.history_id, 'ext': 'lav', 'name': 'LAJ Output', 'info': 'Added by LAJ', 'dbkey': dataset.dbkey, 'copy_access_from': dataset.id }.items() ) ),
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
