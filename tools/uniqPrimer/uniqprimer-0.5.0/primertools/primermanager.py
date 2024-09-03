'''
Created on Jan 1, 2011

@author: John L. Herndon
@contact: herndon@cs.colostate.edu
@organization: Colorado State University
@group: Computer Science Department, Asa Ben-Hur's laboratory 
'''

import utils
import tempfile
import programs
import eprimerparser
import primersearchutils
import fastaparser
import exceptions




class PrimerManager( object ):
    '''
    A class used to find primers given a set of sequences.
    '''

    def __init__( self, eprimerOptions ):
        self.eprimer = programs.Eprimer( eprimerOptions )
        self.primersearch = programs.PrimerSearch( )
    
                
    def findPrimers( self, sequences, outputFile, primerpairs = 20, returnPrimers = False ):
        '''
        A method to find a set of primers based on the given sequences
        '''
        
        utils.logMessage( "PrimerManager::findPrimer(s )", "writing sequences to a fasta file" )
        
        #eleminate all sequences that are lees than the desired amplification size...
       
        if len( sequences ) == 4 :
            print sequences
        sequences = filter( lambda x: len( x ) >= 200, sequences )
        
        primerFastaFile = utils.getTemporaryDirectory( ) + "/sequenceForEprimer.fasta"
        fastaparser.writeFastaFile( sequences, primerFastaFile )

        utils.logMessage( "PrimerManager::findPrimers( )", "executing eprimer3 program" )
        self.eprimer.execute( [ primerFastaFile, outputFile ] )
        utils.logMessage( "PrimerManager::findPrimer( )", "eprimer3 file {0} created. Parsing for primers.".format( outputFile ) )
        
        primers = eprimerparser.parsePrimerSequences( outputFile )
        
        utils.logMessage( "PrimerManager::findPrimers( )", "parsing for sequences complete" )
        
        if returnPrimers == True:
            return primers
        
    
    def getPrimers( self, sequences ):
        
        utils.logMessage( "PrimerManager::getCommonPrimers", "finding primers that are common to all include files" )
            
        if len( sequences ) == 0:
            raise utils.NoPrimersExistException( )
        
        referenceEPrimerFile = utils.getTemporaryDirectory( ) + "/referenceprimers.ep3"
        
        #run eprimer to find primers in the reference file
        primers = self.findPrimers( sequences, referenceEPrimerFile, 20, True )
        
        
        if len( primers ) == 0:
             raise utils.NoPrimersExistException( )
        
        return primers
 
    def crossValidatePrimers2( self, primers, includeFile, j ):    
        includeSequences = fastaparser.parseFastaFile( includeFile )
        #write a primer search input file with using the primers argument
        primerInputFileName = utils.getTemporaryDirectory( ) + "/tmpinputprimers2.ps" + str(j)
        primerOutputFileName = utils.getTemporaryDirectory( ) + "/tmpoutputprimers2.ps" + str(j)
        primersearchutils.writePrimerSearchInputFile( primers, primerInputFileName )

        utils.logMessage( "PrimerManager::crossValidatePrimers", "finding primers that are in the supplied include file" )
        #run primer search to identify the primers
        self.primersearch.execute( [ includeFile, primerInputFileName, primerOutputFileName, "0" ] )

        #read the found primers from the file
        commonPrimers = primersearchutils.parsePrimerSearchFile( primerOutputFileName )

        #compose a list of primers that are not found in the exclude file...
        returnValue = [ ]

        for primer in primers:
            if primer.id in commonPrimers:
                returnValue.append( primer )

        utils.logMessage( "PrimerManager::crossValidatePrimers", "{0} unique primers identified out of {1}".format( len( returnValue ), len( primers ) ) )

        if len( returnValue  ) == 0:
            raise utils.NoPrimersExistException( )

        return returnValue

    
    def crossValidatePrimers( self, primers, excludeFile ):             
        
        excludeSequences = fastaparser.parseFastaFile( excludeFile )
        
        #write a primer search input file with using the primers argument
        primerInputFileName = utils.getTemporaryDirectory( ) + "/tmpinputprimers.ps"
        primerOutputFileName = utils.getTemporaryDirectory( ) + "/tmpoutputprimers.ps"
        primersearchutils.writePrimerSearchInputFile( primers, primerInputFileName )
        
        utils.logMessage( "PrimerManager::crossValidatePrimers", "finding primers that are not in the supplied exclude file" )
        #run primer search to identify the primers
        self.primersearch.execute( [ excludeFile, primerInputFileName, primerOutputFileName, "10" ] )
        
        #read the found primers from the file
        commonPrimers = primersearchutils.parsePrimerSearchFile( primerOutputFileName )
        
        #compose a list of primers that are not found in the exclude file...
        returnValue = [ ]
        
        for primer in primers:
            if primer.id not in commonPrimers:
                returnValue.append( primer )
        
        utils.logMessage( "PrimerManager::crossValidatePrimers", "{0} unique primers identified out of {1}".format( len( returnValue ), len( primers ) ) )
        
        if len( returnValue  ) == 0:
            raise utils.NoPrimersExistException( )
        
        return returnValue
    
    
    
