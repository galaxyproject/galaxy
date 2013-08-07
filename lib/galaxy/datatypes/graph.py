"""
Graph content classes.
"""

import data, tabular, xml

import logging
log = logging.getLogger( __name__ )


class Xgmml( xml.GenericXml ):
    """
    XGMML graph format
    (http://wiki.cytoscape.org/Cytoscape_User_Manual/Network_Formats).
    """
    file_ext = "xgmml"

    def set_peek( self, dataset, is_multi_byte=False ):
        """
        Set the peek and blurb text
        """
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = 'XGMML data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def sniff( self, filename ):
        """
        Determines whether the file is XML or not, should probably actually check if it is a real xgmml file....
        """
        line = ''
        with open( filename ) as handle:
            line = handle.readline()

        #TODO - Is there a more robust way to do this?
        return line.startswith( '<?xml ' )

    @staticmethod
    def merge( split_files, output_file ):
        """
        Merging multiple XML files is non-trivial and must be done in subclasses.
        """
        if len( split_files ) > 1:
            raise NotImplementedError( "Merging multiple XML files is non-trivial "
                                     + "and must be implemented for each XML type" )
        #For one file only, use base class method (move/copy)
        data.Text.merge( split_files, output_file )


class Sif( tabular.Tabular ):
    """
    SIF graph format
    (http://wiki.cytoscape.org/Cytoscape_User_Manual/Network_Formats).

    First column: node id
    Second column: relationship type
    Third to Nth column: target ids for link
    """
    file_ext = "sif"

    def set_peek( self, dataset, is_multi_byte=False ):
        """
        Set the peek and blurb text
        """
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = 'SIF data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def sniff( self, filename ):
        """
        Determines whether the file is SIF
        """
        print '---------------------------------------- sniffing Siffing'
        line = ''
        with open( filename ) as infile:
            correct = True
            for line in infile:
                if not line.strip():
                    continue
                tlen = len( line.split( "\t" ) )
                # may contain 1 or >= 3 columns
                if tlen == 2:
                    correct = False
        return correct

    @staticmethod
    def merge( split_files, output_file ):
        data.Text.merge( split_files, output_file )


#TODO: we might want to look at rdflib or a similar, larger lib/egg
class Rdf( xml.GenericXml ):
    """
    Resource Description Framework format (http://www.w3.org/RDF/).
    """
    file_ext = "rdf"

    def set_peek( self, dataset, is_multi_byte=False ):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = 'RDF data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
