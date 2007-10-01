"""
Image classes
"""

import data
import logging
from galaxy.datatypes.sniff import *
from urllib import urlencode
import zipfile

log = logging.getLogger(__name__)

class Image( data.Data ):
    """Class describing an image"""
    def set_peek( self, dataset ):
        dataset.peek  = 'Image in %s format (%s)' % ( dataset.extension, data.nice_size( dataset.get_size() ) )
        dataset.blurb = 'image' 

class Gmaj( data.Data ):
    """Class describing a GMAJ Applet"""
    file_ext = "gmaj.zip"

    def set_peek( self, dataset ):
        dataset.peek  = "<p align=\"center\"><applet code=\"edu.psu.bx.gmaj.MajApplet.class\" archive=\"/static/gmaj/gmaj.jar\" width=\"200\" height=\"30\" align=\"middle\"> <param name=bundle value=\"display?id="+str(dataset.id)+"&tofile=yes&toext=.zip\"> <param name=buttonlabel value=\"Launch GMAJ\"><param name=nobutton value=\"false\"><param name=urlpause value=\"100\"><param name=debug value=\"false\"><i>Your browser is not responding to the &lt;applet&gt; tag.</i></applet></p>"
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
        export_url = "/history_add_to?"+urlencode({'history_id':dataset.history_id,'ext':'lav','name':'LAJ Output','info':'Added by LAJ','dbkey':dataset.dbkey})
        dataset.peek  = "<p align=\"center\"><applet code=\"edu.psu.cse.bio.laj.LajApplet.class\" archive=\"static/laj/laj.jar\" width=\"200\" height=\"30\"><param name=buttonlabel value=\"Launch LAJ\"><param name=title value=\"LAJ in Galaxy\"><param name=posturl value=\""+export_url+"\"><param name=alignfile1 value=\"display?id="+str(dataset.id)+"\"><param name=noseq value=\"true\"></applet></p>"
        dataset.blurb = 'LAJ Multiple Alignment Viewer'
    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "peek unavailable"

