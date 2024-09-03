'''
Created on Jan 1, 2011

@author: John L. Herndon
@contact: herndon@cs.colostate.edu
@organization: Colorado State University
@group: Computer Science Department, Asa Ben-Hur's laboratory 
'''


import fastaparser
import utils
import os
import programs
import nucmerparser
import copy

class IncludeFileManager( object ):
    """
    A class to manage include files
    """
    #This class needs some work. Need to come up with a way to find unique sequences between all include files....

    def __init__( self ):
        """
        Constructor
        """
        self.includeFiles = [ ]
        self.nucmer = programs.Nucmer( )
        self.isExcludeFileInitialized = False
        self.isReferenceFileInitialized = False
        self.referenceFile = None
        self.referenceSequence = None
        self.uniqueSequences = None
          
    def setExcludeFile( self, excludeFileName ):
        """
        A function to set the exclude file that will be used when nucmer is called
        """
        
        utils.logMessage( "IncludeFileManager::setExcludeFile( )", "fileName {0}".format( excludeFileName ) )
        self.excludeFileName = excludeFileName
        self.isExcludeFileInitialized = True
    
  
    def findUniqueSequencesInFile(self, doWantFile, doNotWantFile ):
        utils.logMessage( "IncludeFileManager::findUniqueSequence( )", "running nucmer for reference file: {0}".format( doWantFile ) )
        coordFile = self.nucmer.execute( [ doWantFile, doNotWantFile ] )
        
        matches = nucmerparser.parseCoordMatchFile( coordFile )
        sequences = fastaparser.parseFastaFileAsPrimerSequence( doWantFile )
        
        for match in matches:
            if sequences.has_key( match.seqID ):
                primerData = sequences[ match.seqID ]
                primerData.addMatch( match )
            else:
                print "Warning: id from .coords file not found in sequence data..."
                utils.logMessage( "IncludeFileManager::processMatches( )", "WARNING - an ID was read in a Match that does not correspond to a sequence read from the fasta file!" )
        
        returnValue = [ ]
    
        for key in sequences.keys( ):
            sequence = sequences[ key ]
            subSequences = sequence.getNonMatchedSubSequences( )
            returnValue.extend( subSequences )
            
        return returnValue
        
        
    def findCommonSequencesInFile(self, want, alsoWant ):
         utils.logMessage( "IncludeFileManager::findUniqueSequence( )", "running nucmer for reference file: {0}".format( want ) )
         
         print want, alsoWant
         coordFile = self.nucmer.execute( [ want, alsoWant ] )
         
         matches = nucmerparser.parseCoordMatchFile( coordFile )
         sequences = fastaparser.parseFastaFileAsPrimerSequence( want )
         
         for match in matches:
             if sequences.has_key( match.seqID ):
                 primerData = sequences[ match.seqID ]
                 primerData.addMatch( match )
         
         returnValue = [ ]
         for key in sequences:
             sequence = sequences[ key ]
             subSequences = sequence.getMatchedSubSequences( )
             returnValue.extend( subSequences )
             
             
         return returnValue
         
 
    def processIncludeFile( self, includeFileName ):
        """
        A function that adds and processes and include file.
        An exclude file must be set for this function to be called.
        """
        
        utils.logMessage( "IncludeFileManager::processIncludeFile( )", "processing {0}".format( includeFileName ) )
        
        if self.isExcludeFileInitialized == False:
            utils.logMessage( "IncludeFileManager::processIncludeFile( )", "no exclude file set".format( includeFileName ) )
            raise utils.ModuleNotInitializedException( "includefilemanager", "no exclude file set" )
        
        if self.isReferenceFileInitialized == False:
            
            utils.logMessage( "IncludeFileManager::processIncludeFile( )", "running nucmer for reference file: {0}".format( includeFileName ) )
            self.uniqueSequences = self.findUniqueSequencesInFile( includeFileName, self.excludeFileName )
            
            self.referenceFile = includeFileName
            self.isReferenceFileInitialized = True
            
        else:
            #write the unique sequences to a temp file
            tempSequences = utils.getTemporaryDirectory( ) + "/tempSequences.fasta"
            fastaparser.writeFastaFile( self.uniqueSequences, tempSequences )
            self.findCommonSequencesInFile( includeFileName, tempSequences )
            self.includeFiles.append( includeFileName )
            

    def getUniqueSequences( self ):
        """
        getUniqueSequences - return a dictionary of all sequences that are found in include fasta files, but not the 
        combined exclude fasta files. The dictionary is indexed by the file ID
        """
        
        return self.uniqueSequences
        
        
   