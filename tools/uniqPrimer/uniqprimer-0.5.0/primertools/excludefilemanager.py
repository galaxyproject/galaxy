'''
Created on Jan 16, 2011

@author: jlh
'''
import utils
import fastaparser
from Bio import SeqIO
import os

class ExcludeFileManager( object ):
    '''
    A class to manage fasta files to be excluded
    '''

    def __init__( self ):
        """
        Initialize the ExcludeFileManager
        """
        self.excludeFiles = [ ]
        self.outputFile = ""
    
    def getOutputFileName( self ):
        """
         get the name of the file combined-sequence fasta file
        """
        return self.outputFile
    
    def addExcludeFile( self,  excludeFile ):
        """
        add a file to be managed by the ExcludeFileManager
        """
        
        if os.path.exists( excludeFile ) == False:
            utils.logMessage( "ExcludeFileManager::addExcludeFile( )", "exclude file not found: {0}".format( excludeFile ) )
            raise utils.NoFileFoundException( excludeFile )
        
        utils.logMessage( "ExcludeFileManager::addExcludeFile( )", "adding exclude file {0}".format( excludeFile ) )
        self.excludeFiles.append( excludeFile )
    
    def buildOutputFileName( self ):
        """
        build a unique file name to store the combined output sequences to
        """
        self.outputFile = utils.getTemporaryDirectory( ) + "/combined_exlude.ffn"
        utils.logMessage( "ExcludeFileManager::buildOutputFileName( )", " exclude file: {0}".format( self.outputFile ) )
    
    def exportSequences( self ):
        """
        combine all exclude files into a single exclude file
        """
        
        utils.logMessage( "ExcludeFileManager::exportSequences( )", "parsing exclude sequences")
        
        #read all exclude file sequences into memory
        sequences = [ ]
        for excludeFile in self.excludeFiles:
            sequences.extend( fastaparser.parseFastaFile( excludeFile ) )
        
        utils.logMessage( "ExcludeFileManager::exportSequences( )", "finished parsing, writing to a common file"  )
        
        self.buildOutputFileName( )
        #combine the sequences and write them to a file
        
        SeqIO.write( sequences, open( self.outputFile, "w" ), "fasta" )
         
        utils.logMessage( "ExcludeFileManager::exportSequences( )", "All sequences exported" )
        
        
        
        
        
    
    
        