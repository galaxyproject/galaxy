"""
XML format classes
"""
import data
import logging
from galaxy.datatypes.sniff import *

log = logging.getLogger(__name__)

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
        >>> fname = get_test_fname( 'tblastn_four_human_vs_rhodopsin.xml' )
        >>> BlastXml().sniff( fname )
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

class BlastXml( GenericXml ):
    """NCBI Blast XML Output data"""
    file_ext = "blastxml"

    def set_peek( self, dataset, is_multi_byte=False ):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = 'NCBI Blast XML data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
    def sniff( self, filename ):
        """
        Determines whether the file is blastxml
        
        >>> fname = get_test_fname( 'megablast_xml_parser_test1.blastxml' )
        >>> BlastXml().sniff( fname )
        True
        >>> fname = get_test_fname( 'tblastn_four_human_vs_rhodopsin.xml' )
        >>> BlastXml().sniff( fname )
        True
        >>> fname = get_test_fname( 'interval.interval' )
        >>> BlastXml().sniff( fname )
        False
        """
        #TODO - Use a context manager on Python 2.5+ to close handle
        handle = open(filename)
        line = handle.readline()
        if line.strip() != '<?xml version="1.0"?>':
            handle.close()
            return False
        line = handle.readline()
        if line.strip() not in ['<!DOCTYPE BlastOutput PUBLIC "-//NCBI//NCBI BlastOutput/EN" "http://www.ncbi.nlm.nih.gov/dtd/NCBI_BlastOutput.dtd">',
                                '<!DOCTYPE BlastOutput PUBLIC "-//NCBI//NCBI BlastOutput/EN" "NCBI_BlastOutput.dtd">']:
            handle.close()
            return False
        line = handle.readline()
        if line.strip() != '<BlastOutput>':
            handle.close()
            return False
        handle.close()
        return True
        

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
