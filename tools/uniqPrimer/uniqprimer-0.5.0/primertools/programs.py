'''
Created on Jan 1, 2011

@author: John L. Herndon
@contact: herndon@cs.colostate.edu
@organization: Colorado State University
@group: Computer Science Department, Asa Ben-Hur's laboratory 
'''


import utils
import os
import subprocess


class ProgramBase( object ):
    
    def __init__( self ):
    
        self.programName = None
        self.proc = None
    
    def getProcessArgs( self, args ):
        crash #abstract
        
    def execute( self, args, async = False ):
        '''
        run the nucmer program with a given compare file and an exclude file
        '''
        
        utils.logMessage( "ProgramBase::Execute( )", "Running the {0} program.".format( self.programName ) )
        
        args, outputFile = self.getProcessArgs( args )
        
        print "*** Running {0} ***".format( self.programName )
        
        utils.logList( "ProgramBase::Execute( )", args )
        
        proc = subprocess.Popen( args )
        
        if async == False:
            #wait for the nucmer instance to finish
            proc.wait( )
            print "*** Running {0} Complete ***".format( self.programName )
        
        #return the name of the coords file
        return outputFile
    
    def isFinished( self ):
        ifIsFinished 
        
class Nucmer( ProgramBase ):
    
    def __init__( self ):
        #if we can't find the nucemer binary, throw
        nucmerPath = utils.search_file( 'nucmer' )
        ProgramBase.__init__( self )
        if nucmerPath is None:
            raise utils.ProgramNotFoundException( 'nucmer', "Please ensure that the MUMmer package is installed and configured on your system." )
        
        self.nucmer = nucmerPath

        self.programName = "nucmer"
        self.outputExtension = ".coords"
        
        
    def getProcessArgs( self, inputArgs ):
        
        
        time = utils.getTimeStamp( )
        
        identifier =  "nucmer_alignments"
        args = [ self.nucmer, '-p', identifier, '-o', '--minmatch', '300', '--maxgap', '1' ]
        
        args.extend( inputArgs )
    
        outputFile = "{0}.coords".format( identifier )
        
        return args, outputFile

class Eprimer( ProgramBase ):
    
    def __init__( self, eprimerOptions ):
            
        self.programName = "EPrimer3"
        self.options = eprimerOptions
        
        primer3corePath = utils.search_file( "primer3_core" )
        if primer3corePath is None:
            raise utils.ProgramNotFoundException( "primer3_core", "Please ensure that the primer3 package is installed on your system. It can be obtained from http://primer3.sourceforge.net/" )
        
        eprimerPath = utils.search_file( "eprimer3" )
        if eprimerPath is None:
            raise utils.ProgramNotFoundException( 'eprimer3', "Please ensure that the EMBOSS package is installed and configured on your system." )
        
        self.primer3core = primer3corePath
        self.eprimer3 = eprimerPath
        
    def getProcessArgs( self, inputArgs ):

        #todo - allow user to determine output file location/name
        
        inputFasta = inputArgs[ 0 ]
        outputFile = inputArgs[ 1 ]
        args = [ self.eprimer3, inputFasta, outputFile, '-numreturn', '2', '-prange', self.options.getProductRange( ), '-osize', str( self.options.getPrimerSize( ) ),
                '-minsize', str( self.options.getMinPrimerSize( ) ), '-maxsize', str( self.options.getMaxPrimerSize( ) )]
        
        return args, outputFile
    
class PrimerSearch( ProgramBase ):
    def __init__( self ):    

        self.programName = "PrimerSearch"
        primerSearchPath = utils.search_file( "primersearch" )
        if primerSearchPath is None:
            raise utils.ProgramNotFoundException( "primersearch", "Please ensure that the EMBOSS package is installed on your system." )
    
        self.primerSearch = primerSearchPath
        
    def getProcessArgs( self, inputArgs ):
        '''
        usage for this program: inputArgs is an array length 4
        inputArgs[0] = sequence file
        inputArgs[1] = primer pairs file
        inputArgs[2] = output file name
        inputArgs[3] = percent mismatch
        '''
        
        args = [ self.primerSearch ]
        args.extend( [ '-seqall', inputArgs[ 0 ] ] ) 
        args.extend( [ '-infile', inputArgs[ 1 ] ] )
        args.extend( [ '-mismatchpercent', inputArgs[ 3 ] ] )
        args.extend( [ '-outfile', inputArgs[ 2 ] ] ) 
    
    
        return args, inputArgs[ 2 ]
    
    
    
    
        
