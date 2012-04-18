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
    
    def merge(split_files, output_file):
        """Merging multiple XML files is non-trivial and must be done in subclasses."""
        if len(split_files) == 1:
            #For one file only, use base class method (move/copy)
            return data.Text.merge(split_files, output_file)
        out = open(output_file, "w")
        h = None
        for f in split_files:
            h = open(f)
            body = False
            header = h.readline()
            if not header:
                out.close()
                h.close()
                raise ValueError("BLAST XML file %s was empty" % f)
            if header.strip() != '<?xml version="1.0"?>':
                out.write(header) #for diagnosis
                out.close()
                h.close()
                raise ValueError("%s is not an XML file!" % f)
            line = h.readline()
            header += line
            if line.strip() not in ['<!DOCTYPE BlastOutput PUBLIC "-//NCBI//NCBI BlastOutput/EN" "http://www.ncbi.nlm.nih.gov/dtd/NCBI_BlastOutput.dtd">',
                                    '<!DOCTYPE BlastOutput PUBLIC "-//NCBI//NCBI BlastOutput/EN" "NCBI_BlastOutput.dtd">']:
                out.write(header) #for diagnosis
                out.close()
                h.close()
                raise ValueError("%s is not a BLAST XML file!" % f)
            while True:
                line = h.readline()
                if not line:
                    out.write(header) #for diagnosis
                    out.close()
                    h.close()
                    raise ValueError("BLAST XML file %s ended prematurely" % f)
                header += line
                if "<Iteration>" in line:
                    break
                if len(header) > 10000:
                    #Something has gone wrong, don't load too much into memory!
                    #Write what we have to the merged file for diagnostics
                    out.write(header)
                    out.close()
                    h.close()
                    raise ValueError("BLAST XML file %s has too long a header!" % f)
            if "<BlastOutput>" not in header:
                out.close()
                h.close()
                raise ValueError("%s is not a BLAST XML file:\n%s\n..." % (f, header))
            if f == split_files[0]:
                out.write(header)
                old_header = header
            elif old_header[:300] != header[:300]:
                #Enough to check <BlastOutput_program> and <BlastOutput_version> match
                out.close()
                h.close()
                raise ValueError("BLAST XML headers don't match for %s and %s - have:\n%s\n...\n\nAnd:\n%s\n...\n" \
                                 % (split_files[0], f, old_header[:300], header[:300]))
            else:
                out.write("    <Iteration>\n")
            for line in h:
                if "</BlastOutput_iterations>" in line:
                    break
                #TODO - Increment <Iteration_iter-num> and if required automatic query names
                #like <Iteration_query-ID>Query_3</Iteration_query-ID> to be increasing?
                out.write(line)
            h.close()
        out.write("  </BlastOutput_iterations>\n")
        out.write("</BlastOutput>\n")
        out.close()
    merge = staticmethod(merge)
                                                

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
