"""
XML format classes
"""
import data
import logging
from galaxy.datatypes.sniff import *
import dataproviders

log = logging.getLogger(__name__)

@dataproviders.decorators.has_dataproviders
class GenericXml( data.Text ):
    """Base format class for any XML file."""
    file_ext = "xml"

    def set_peek( self, dataset, is_multi_byte=False ):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = 'XML data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def sniff( self, filename ):
        """
        Determines whether the file is XML or not

        >>> fname = get_test_fname( 'megablast_xml_parser_test1.blastxml' )
        >>> GenericXml().sniff( fname )
        True
        >>> fname = get_test_fname( 'interval.interval' )
        >>> GenericXml().sniff( fname )
        False
        """
        #TODO - Use a context manager on Python 2.5+ to close handle
        handle = open(filename)
        line = handle.readline()
        handle.close()

        #TODO - Is there a more robust way to do this?
        return line.startswith('<?xml ')

    def merge(split_files, output_file):
        """Merging multiple XML files is non-trivial and must be done in subclasses."""
        if len(split_files) > 1:
            raise NotImplementedError("Merging multiple XML files is non-trivial and must be implemented for each XML type")
        #For one file only, use base class method (move/copy)
        data.Text.merge(split_files, output_file)
    merge = staticmethod(merge)

    @dataproviders.decorators.dataprovider_factory( 'xml', dataproviders.hierarchy.XMLDataProvider.settings )
    def xml_dataprovider( self, dataset, **settings ):
        dataset_source = dataproviders.dataset.DatasetDataProvider( dataset )
        return dataproviders.hierarchy.XMLDataProvider( dataset_source, **settings )


class MEMEXml( GenericXml ):
    """MEME XML Output data"""
    file_ext = "memexml"

    def set_peek( self, dataset, is_multi_byte=False ):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = 'MEME XML data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
    def sniff( self, filename ):
        return False


class CisML( GenericXml ):
    """CisML XML data""" #see: http://www.ncbi.nlm.nih.gov/pubmed/15001475
    file_ext = "cisml"

    def set_peek( self, dataset, is_multi_byte=False ):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = 'CisML data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
    def sniff( self, filename ):
        return False


class Phyloxml( GenericXml ):
    """Format for defining phyloxml data http://www.phyloxml.org/"""
    file_ext = "phyloxml"
    def set_peek( self, dataset, is_multi_byte=False ):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = 'Phyloxml data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def sniff( self, filename ):
        """"Checking for keyword - 'phyloxml' always in lowercase in the first few lines"""

        f = open( filename, "r" )
        firstlines = "".join( f.readlines(5) )
        f.close()

        if "phyloxml" in firstlines:
            return True
        return False

    def get_visualizations( self, dataset ):
        """
        Returns a list of visualizations for datatype.
        """

        return [ 'phyloviz' ]
