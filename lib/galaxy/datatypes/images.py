"""
Image classes
"""

import data
import logging
from galaxy.datatypes.sniff import *
from urllib import urlencode
import zipfile

log = logging.getLogger(__name__)

class Ab1( data.Data ):
    """Class describing an ab1 binary sequence file"""
    file_ext = "ab1"
    def set_peek( self, dataset ):
        export_url = "/history_add_to?"+urlencode({'history_id':dataset.history_id,'ext':'ab1','name':'ab1 sequence','info':'Sequence file','dbkey':dataset.dbkey})
        dataset.peek  = "Binary ab1 sequence file (%s)" % ( data.nice_size( dataset.get_size() ) )
        dataset.blurb = "Binary ab1 sequence file"
    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "Binary ab1 sequence file (%s)" % ( data.nice_size( dataset.get_size() ) )

class Scf( data.Data ):
    """Class describing an scf binary sequence file"""
    file_ext = "scf"
    def set_peek( self, dataset ):
        export_url = "/history_add_to?"+urlencode({'history_id':dataset.history_id,'ext':'scf','name':'scf sequence','info':'Sequence file','dbkey':dataset.dbkey})
        dataset.peek  = "Binary scf sequence file (%s)" % ( data.nice_size( dataset.get_size() ) )
        dataset.blurb = "Binary scf sequence file"
    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "Binary scf sequence file (%s)" % ( data.nice_size( dataset.get_size() ) )

class Binseq( data.Data ):
    """Class describing a zip archive of binary sequence files"""
    file_ext = "binseq.zip"
    def set_peek( self, dataset ):
        zip_file = zipfile.ZipFile( dataset.file_name, "r" )
        num_files = len( zip_file.namelist() )
        dataset.peek  = "Binary sequence file archive (%s)" % ( data.nice_size( dataset.get_size() ) )
        dataset.blurb = 'Zip archive of %s binary sequence files' % ( str( num_files ) )
    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "Binary sequence file archive (%s)" % ( data.nice_size( dataset.get_size() ) )
    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'application/zip'

class Txtseq( data.Data ):
    """Class describing a zip archive of text sequence files"""
    file_ext = "txtseq.zip"
    def set_peek( self, dataset ):
        zip_file = zipfile.ZipFile( dataset.file_name, "r" )
        num_files = len( zip_file.namelist() )
        dataset.peek  = "Text sequence file archive (%s)" % ( data.nice_size( dataset.get_size() ) )
        dataset.blurb = 'Zip archive of %s text sequence files' % ( str( num_files ) )
    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "Text sequence file archive (%s)" % ( data.nice_size( dataset.get_size() ) )
    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'application/zip'

class Image( data.Data ):
    """Class describing an image"""
    def set_peek( self, dataset ):
        dataset.peek  = 'Image in %s format (%s)' % ( dataset.extension, data.nice_size( dataset.get_size() ) )
        dataset.blurb = 'image' 

def create_applet_tag_peek( class_name, archive, params ):
    text = """
<!--[if !IE]>-->
<object classid="java:%s" 
      type="application/x-java-applet"
      height="30" width="200" align="center" >
      <param name="archive" value="%s"/>""" % ( class_name, archive )
    for name, value in params.iteritems():
        text += """<param name="%s" value="%s"/>""" % ( name, value )
    text += """
<!--<![endif]-->
<object classid="clsid:8AD9C840-044E-11D1-B3E9-00805F499D93" 
        height="30" width="200" >
        <param name="code" value="%s" />
        <param name="archive" value="%s"/>""" % ( class_name, archive )
    for name, value in params.iteritems():
        text += """<param name="%s" value="%s"/>""" % ( name, value )
    text += """</object> 
<!--[if !IE]>-->
</object>
<!--<![endif]-->
"""
    return """<div><p align="center">%s</p></div>""" % text

class Gmaj( data.Data ):
    """Class describing a GMAJ Applet"""
    file_ext = "gmaj.zip"
    def set_peek( self, dataset ):
        params = {
        "bundle":"display?id=%s&tofile=yes&toext=.zip" % dataset.id,
        "buttonlabel": "Launch GMAJ",
        "nobutton": "false",
        "urlpause" :"100",
        "debug": "false",
        }
        class_name = "edu.psu.bx.gmaj.MajApplet.class"
        archive = "/static/gmaj/gmaj.jar"
        dataset.peek = create_applet_tag_peek( class_name, archive, params )
        dataset.blurb = 'GMAJ Multiple Alignment Viewer'
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
    def set_peek( self, dataset ):
        dataset.peek  = "HTML file (%s)" % ( data.nice_size( dataset.get_size() ) )
        dataset.blurb = data.nice_size( dataset.get_size() )
    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'text/html'
    def sniff( self, filename ):
        """
        Determines wether the file is in html format

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
    def set_peek( self, dataset ):
        params = {
        "alignfile1": "display?id=%s" % dataset.id,
        "buttonlabel": "Launch LAJ",
        "title": "LAJ in Galaxy",
        "posturl": "history_add_to?%s" % urlencode( { 'history_id': dataset.history_id, 'ext': 'lav', 'name': 'LAJ Output', 'info': 'Added by LAJ', 'dbkey': dataset.dbkey } ),
        "noseq": "true"
        }
        class_name = "edu.psu.cse.bio.laj.LajApplet.class"
        archive = "/static/laj/laj.jar"
        dataset.peek = create_applet_tag_peek( class_name, archive, params )
        dataset.blurb = 'LAJ Multiple Alignment Viewer'
    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "peek unavailable"
