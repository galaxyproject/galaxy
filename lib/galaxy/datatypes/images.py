"""
Image classes
"""

import data
import logging
from urllib import urlencode

log = logging.getLogger(__name__)

class Image( data.Data ):
    """Class describing an image"""
    def set_peek( self, dataset ):
        dataset.peek  = 'Image in %s format (%s)' % ( dataset.extension, data.nice_size( dataset.get_size() ) )
        dataset.blurb = 'image' 

class Gmaj( data.Data ):
    """Class describing a GMAJ Applet"""
    def set_peek( self, dataset ):
        dataset.peek  = "<p align=\"center\"><applet code=\"edu.psu.bx.gmaj.MajApplet.class\" archive=\"static/gmaj/gmaj.jar\" width=\"200\" height=\"30\" align=\"middle\"> <param name=bundle value=\"display?id="+str(dataset.id)+"&tofile=yes&toext=.zip\"> <param name=buttonlabel value=\"Launch GMAJ\"><param name=nobutton value=\"false\"><param name=urlpause value=\"100\"><param name=debug value=\"false\"><i>Your browser is not responding to the &lt;applet&gt; tag.</i></applet></p>"
        dataset.blurb = 'GMAJ Multiple Alignment Viewer'
        
    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "peek unavailable"
            
class Laj( data.Text ):
    """Class describing a LAJ Applet"""
    def set_peek( self, dataset ):
        export_url = "/history_add_to?"+urlencode({'history_id':dataset.history_id,'ext':'lav','name':'LAJ Output','info':'Added by LAJ','dbkey':dataset.dbkey})
        dataset.peek  = "<p align=\"center\"><applet code=\"edu.psu.cse.bio.laj.LajApplet.class\" archive=\"static/laj/laj.jar\" width=\"200\" height=\"30\"><param name=buttonlabel value=\"Launch LAJ\"><param name=title value=\"LAJ in Galaxy\"><param name=posturl value=\""+export_url+"\"><param name=alignfile1 value=\"display?id="+str(dataset.id)+"\"><param name=noseq value=\"true\"></applet></p>"
        dataset.blurb = 'LAJ Multiple Alignment Viewer'
        
    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "peek unavailable"
            
class Html( data.Text ):
    """Class describing an html file"""
    def set_peek( self, dataset ):
        dataset.peek  = "HTML file (%s)" % ( data.nice_size( dataset.get_size() ) )
        dataset.blurb = data.nice_size( dataset.get_size() )
        
    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "peek unavailable"