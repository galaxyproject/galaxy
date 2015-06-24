"""
Triple format classes
"""
import re
import data
import logging
from galaxy.datatypes.sniff import *
import dataproviders
import xml
import text
import json
import os

log = logging.getLogger(__name__)

class Triples( data.Text ):
    """
    The abstract base class for the file format that can contain triples
    """
    edam_format = "format_2376"
    file_ext = "triples"

    def sniff( self, filename ):
        """
        Returns false and the user must manually set.
        """
        return False

    def set_peek( self, dataset, is_multi_byte=False ):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = 'Triple data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

class NTriples( Triples ):
    """
    The N-Triples triple data format
    """
    edam_format = "format_3256"
    file_ext = "nt"

    def sniff( self, filename ):
        handle = open(filename)
        line = handle.readline()
        handle.close()
             
        #@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .  
        if re.compile( r'<[^>]*>\s<[^>]*>\s<[^>]*>\s\.' ).search( line ):
            return True 
        return False

    def set_peek( self, dataset, is_multi_byte=False ):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = 'N-Triples triple data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

class N3( Triples ):
    """
    The N3 triple data format
    """
    edam_format = "format_3257"
    file_ext = "n3"

    def sniff( self, filename ):
        """
        Returns false and the user must manually set.
        """
        return False

    def set_peek( self, dataset, is_multi_byte=False ):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = 'Notation-3 Triple data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

class Turtle( Triples ):
    """
    The Turtle triple data format
    """
    edam_format = "format_3255"
    file_ext = "ttl"

    def sniff( self, filename ):
        handle = open(filename)
        line = handle.readline()
        handle.close()
             
        #@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .  
        if re.compile( r'@prefix\s+[^:]*:\s+<[^>]*>\s\.' ).search( line ):
            return True 

        return False

    def set_peek( self, dataset, is_multi_byte=False ):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = 'Turtle triple data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

#TODO: we might want to look at rdflib or a similar, larger lib/egg
class Rdf( xml.GenericXml, Triples ):
    """
    Resource Description Framework format (http://www.w3.org/RDF/).
    """
    edam_format = "format_3261"
    file_ext = "rdf"

    def sniff( self, filename ):
        f = open( filename, "r" )
        firstlines = "".join( f.readlines(5) )
        f.close()

        if "http://www.w3.org/1999/02/22-rdf-syntax-ns#" in firstlines and "RDF" in firstlines:
            return True

        return False

    def set_peek( self, dataset, is_multi_byte=False ):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = 'RDF/XML triple data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

class Jsonld( text.Json, Triples ):
    """
    The JSON-LD data format
    """
    #format not defined in edam so we use the json format number 
    edam_format = "format_3464" 
    file_ext = "jsonld"

    def sniff( self, filename ):
        if self._looks_like_json( filename ): #super( text.Json, self ).sniff( filename )
            f = open( filename, "r" )
            firstlines = "".join( f.readlines(5) )
            f.close()

            if "\"@id\"" in firstlines or "\"@context\"" in firstlines:
                return True
        return False

    def set_peek( self, dataset, is_multi_byte=False ):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = 'JSON-LD triple data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

