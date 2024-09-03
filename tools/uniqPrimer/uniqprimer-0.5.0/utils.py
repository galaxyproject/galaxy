'''
Created on Jan 1, 2011

@author: John L. Herndon
@contact: herndon@cs.colostate.edu
@organization: Colorado State University
@group: Computer Science Department, Asa Ben-Hur's laboratory 
'''


import exceptions
import time
import os.path
from os import pathsep
from string import split
import tempfile
import shutil

def getTimeStamp( ):
    return time.strftime('%d%m%Y-%H%M%S')


class Match( object ):
    '''
    record where two genomes line up. stores only alignments for one part of the genome
    '''
    def __init__( self, start, end, seqID ):
        self.seqID = seqID
        self.start = start
        self.end = end
    
    def __repr__( self ):
        return "Start: {0}, End:{1}, SeqID:{2}".format( self.start, self.end, self.seqID )
    
class PrimerSet( object ):
    
    def __init__( self, id ):
        self.id = id
        self.productSize = 0
        self.forwardPrimer = ""
        self.forwardMeltTemp = ""
        self.reversePrimer = ""
        self.reverseMeltTemp = ""
        
        
    def setProductSize( self, productSize):
        self.productSize = productSize
        
    def setForwardPrimerData( self, sequence, temp ):
        self.forwardPrimer = sequence
        self.forwardMeltTemp = temp
        
    def setReversePrimerData( self, sequence, temp):
        self.reversePrimer = sequence
        self.reverseMeltTemp = temp
    

#search function from http://code.activestate.com/recipes/52224-find-a-file-given-a-search-path/
def search_file( filename ):
    """ find file
    """
    search_path = os.getenv( 'PATH' )
    logMessage( "utils::search_file", "Path: {0}".format( search_path ) )
    file_found = 0
    paths = split( search_path, pathsep )
    for path in paths:
        if os.path.exists( os.path.join( path, filename ) ):
            file_found = 1
            break
    if file_found:
        return os.path.abspath( os.path.join( path, filename ) )
    else:
        return None

tempDir = ""
removeTemp = True

verbose = False


def initialize( isVerbose, cleanup, lf): ##Mau: added lf
    global removeTemp
    global tempDir
    global verbose
    global logFile ##Mau: added  logFile variable

    logFile = lf #:Mau add line
    
    verbose = isVerbose
    tempDir = tempfile.mkdtemp( dir="" )
    initializeLogging()
    removeTemp = cleanup
    logMessage( "utils::Initialize( )", "Initialization complete. Temporary directory: {0}".format( tempDir ) )
    
logFile = None


def printProgressMessage( message ):
    global verbose
    if verbose == True:
        print message

def getTemporaryDirectory( ):
    global tempDir
    return tempDir

def initializeLogging():
    global logFile
    #logFileName = "uniqprimer_{0}.log".format( getTimeStamp( ) )
    #logFileName = "log_uniqprimer.txt"  ##Mau: commented out 
    logFileName = logFile ##Mau: changed
    logFile = open( logFileName, 'w' )
    
def shutdown( ):
    global removeTemp
    global tempDir
    shutdownLogging( )
    if removeTemp == True:
        print "*** Removing temporary directory ***"
        shutil.rmtree( tempDir )
    
def shutdownLogging( ):
    global logFile
    if logFile != None:
        logFile.close( )

def logList( method, list ):
    
    message = reduce( lambda x,y: str( x ) + " " + str( y ) , list )
    logMessage(method, message)
    
    
def logMessage( method, message ):
    global logFile
    if logFile == None:
        return
    log = "{0} - {1}".format( method, message )
    
    logFile.write( log + "\n" )
    logFile.flush( )

class EPrimerOptions( object ):
    
    def __init__( self ):
        
        self.minPrimerSize = 18
        self.maxPrimerSize = 27
        self.primerSize = 20
        self.productRange = "200-250"
    
    def setPrimerSize( self, size ):
        
        size = int( size )
        if size > 35:
            size = 35
        
        self.primerSize = size
        if self.primerSize < self.minPrimerSize:
            self.maxPrimerSize = self.primerSize 
        elif self.primerSize > self.maxPrimerSize:
            self.maxPrimerSize = self.primerSize
    
    def getPrimerSize( self ):
        return self.primerSize
    
    def setMinPrimerSize( self, minSize):
        self.minPrimerSize = minSize
    
    def getMinPrimerSize( self  ):
        return self.minPrimerSize

    def setMaxPrimerSize( self, size ):
        self.maxPrimerSize = size
        
    def getMaxPrimerSize( self ):
        return self.maxPrimerSize
    
    def setProductRange( self, range ):
        self.productRange = range
        
    def getProductRange( self ):
        return self.productRange

class NoPrimersExistException( exceptions.BaseException ):
    
    def __init__( self ):
        exceptions.BaseException( self )

class ProgramNotFoundException( exceptions.BaseException ):
    
    def __init__( self, programName, details ):
        exceptions.BaseException.__init__(self)
        self.programName = programName
        self.details = details
        
class NoFileFoundException( exceptions.BaseException ):
    
    def __init__( self, filename ):
        exceptions.BaseException.__init__(self)
        self.filename = filename
        
        
class ModuleNotInitializedException( exceptions.BaseException ):
    
    def __init__( self, moduleName, reason ):
        self.moduleName = moduleName
        self.reason = reason
