#!/usr/bin/python

'''
Created on Jan 1, 2011

@author: John L. Herndon
@contact: herndon@cs.colostate.edu
@organization: Colorado State University
@group: Computer Science Department, Asa Ben-Hur's laboratory 
'''

import exceptions
import sys
import time
import os ## added by Alexis

sys.path.append("/gs7k1/home/galaxy/galaxy_env/lib/python2.7/site-packages")

import getopt
from primertools import *

version="0.5.0"


class UniqPrimerFinder( object ):
    
    def __init__( self, includeFiles, excludeFiles, crossValidate, eprimerOptions):
        
        utils.logMessage( "UniqPrimerFinder::__init__()", "Initializing UniqPrimerFinder" )
        self.includeFiles = includeFiles
        self.includeFileManager = includefilemanager.IncludeFileManager( )
        
        self.excludeFiles = excludeFiles
        self.excludeFileManager= excludefilemanager.ExcludeFileManager( )
        
        self.primerManager = primermanager.PrimerManager( eprimerOptions )
        
        self.crossValidate = crossValidate

       
        utils.logMessage( "UniqPrimerFinder::__init__()", "Initializing UniqPrimerFinder - complete" )
    
    def writeOutputFile( self, primers, outputFileName, maxresults = 100 ):
        '''
        primers: a list of PrimerSet obs
        '''
        ##outputFileName = uPrimer ##Mau: defined this..
        outputFile = open( outputFileName, 'w' )
        
        i = 0
        for primer in primers:
            i += 1
            
            outputFile.write( "{0}\t{1}\t{2}\t{3}\n".format( i, primer.forwardPrimer, primer.reversePrimer, primer.productSize ) )
            
            if i > maxresults:
                break
            
        utils.logMessage( "UniqPrimerFinder::writeOutputFile()", "output file written." )
            
    
    def findPrimers( self, outputFile = "uPrimer.txt" ):
	outputFile = uPrimer ## Mau adds to overwrite the above value
	

        utils.logMessage( "UniqPrimerFinder::findPrimers()", "Finding primers for include files" )
        startTime = time.time( )
        #generate the combined sequence fasta file for all exclude sequences
        utils.printProgressMessage( "*** Creating Combined Fasta File for Exclude Files ***" )
        for excludeFile in self.excludeFiles:
            self.excludeFileManager.addExcludeFile( excludeFile )
        
        self.excludeFileManager.exportSequences( )
        
        self.includeFileManager.setExcludeFile( self.excludeFileManager.getOutputFileName( ) )

        utils.printProgressMessage( "*** Finding Sequences Unique to Target Genome ***" )

        #run nucmer program on all include files
        for includeFile in self.includeFiles:
            self.includeFileManager.processIncludeFile( includeFile )
                
        #get the sequences found in include files, but no the exclude file. 
        uniqueSequences = self.includeFileManager.getUniqueSequences( )
        
        utils.printProgressMessage( "*** Finding Primers ***" )
        
        primers = self.primerManager.getPrimers( uniqueSequences )
         
        if self.crossValidate == True:
            utils.printProgressMessage( "*** Cross Validating Primers ***" )
            primers = self.primerManager.crossValidatePrimers( primers, self.excludeFileManager.getOutputFileName( ) )
            # added by Alexis, primersearch also against all include files
            #run primersearch program on all include files
            j=0
            for includeFile in self.includeFiles: # added by Alexis
                j = j + 1
                primers = self.primerManager.crossValidatePrimers2( primers, includeFile, j) # added by Alexis
       		
 
        utils.logMessage( "UniqPrimerFinder::findPrimers( )", "found {0} unique sequences".format( len( primers ) ) ) 
        
        self.writeOutputFile( primers, outputFile )
        
        utils.logMessage( "UniqPrimerFinder::findPrimers()", "Finished finding primers" )
        endTime = time.time()
        elapsedMinutes = int( ( endTime - startTime ) / 60 )
        elapsedSeconds = int( ( endTime - startTime ) % 60 )
        print "*** Time Elapsed: {0} minutes, {1} seconds ***".format( elapsedMinutes, elapsedSeconds )
        print "*** Output Written to {0} ***".format( outputFile )
        

def printUsageAndQuit( ):
    global version  
    print "uniqprimer - finds primers unique to a genome"
    print "Version: " + str( version )
    print "Summary of Options."
    print "Required Arguments:"
    print " -i <filename>: use <filename> as an include file. Primers will be identified for this genome"
    print " -x <filename>: use <filename> as an exclude file. Primers for this genome will be excluded"
    print " -o <filename>: specify the name of the unique primer output file (default is uPrimer.txt)" ## Mau added..
    print " -l <filename>: specify the name of the log output file" ## Mau added..
    print " -f <filename>: specify the name of the Fasta of differential sequences" ## Alexis added..

    print "\nOptional Arguments:"
    print " --productsizerage: set a range for the desired size of PCR product (default=200-250). Example: ./uniqprimer -productsizerage 100-150"
    print " --primersize: set the desired primer size (default=20)"
    print " --minprimersize: set the minimum primer size (default=27)"
    print " --maxprimersize: set the maximum primer size (default=18)"
    print " --crossvalidate: force the program to cross validate primers against exclude files for extra certainty"
    print " --keeptempfiles: force the program to keep temporary files"
    
    print "\n\nExample:"
    print "uniqprimer -i <includefile1> -i <includefile2> ... -i <includefileN> -x <excludefile1> -x <excludefile2> ... -x <excludefileN> -o primers.txt -l logfile.txt -f seqForPrimer3.fa"
    utils.shutdownLogging( )
    sys.exit( )


opts = 'i:x:h:o:l:f:' # Mau added :o & :l for outfile specification, Alexis added :f 
longopts=[ "productsizerange=", "primersize=", "minprimersize=", "maxprimersize=", "crossvalidate", "keeptempfiles" ]

def parseArgs( args ):


    global uPrimer ## Mau added lf, brute force...
    global lf # Mau added lf, brute force...
    global fastaDiff # Alexis added fastaDiff
    #uPrimer = "uPrimer.txt" ##the default value...

    crossValidate = False
    cleanup = True
    optlist, args = getopt.getopt( args, opts, longopts )
    
    includeFiles = [ ]
    excludeFiles = [ ]
    eprimerOptions = utils.EPrimerOptions( )
    
    verbose = False
    for opt in optlist:
        if opt[ 0 ] == '-i':
            includeFiles.append( opt[ 1 ] )
        elif opt[ 0 ] == '-x':
            excludeFiles.append( opt[ 1] )
        elif opt[ 0 ] == '-v':
            verbose = True 
        elif opt[ 0 ] == '-o': ## Mau added, if -o...
            uPrimer = str(opt[1])  ## Mau added, then get filename for outfile after -o
        elif opt[ 0 ] == '-l': ## Mau added, if -l...
            lf = str(opt[1])  ## Mau added, then get filename for logfile after -l
        elif opt[ 0 ] == '-f': ## Alexis added, if -f
            fastaDiff = str(opt[1]) ## Alexis added, then get filename for fasta file after -f
        elif opt[ 0 ] == '--productsizerange':
            eprimerOptions.setProductRange( opt[ 1 ] )
            productsizerange = opt[ 1 ]
        elif opt[ 0 ] == '--primersize':
            eprimerOptions.setPrimerSize( opt[1 ] )
        elif opt[ 0 ] == '--minprimersize':
            eprimerOptions.setMinPrimerSize( opt[1 ] )
        elif opt[ 0 ] == '--maxprimersize':
            eprimerOptions.setMaxPrimerSize( opt[1 ] )
        elif opt[ 0 ] == '--crossvalidate':
            crossValidate = True
        elif opt[ 0 ] == '--crossvalidate':
            crossValidate = True
        elif opt[ 0 ] == '--keeptempfiles':
            cleanup = False
        elif opt[ 0 ] == '-h':
            printUsageAndQuit( )
        else:
            print "Unknown option: " + str( opt[ 0 ]  )
            printUsageAndQuit( )
    #print "uPrimer: " + uPrimer + " log file name: " + lf + "\n"
    if len( includeFiles ) == 0 or len( excludeFiles ) == 0:
        
        print "You must specify at least one include file and at least one exclude file"
        printUsageAndQuit( )

    return includeFiles, excludeFiles, crossValidate, cleanup, verbose, eprimerOptions, lf , uPrimer, fastaDiff  #Mau: add lf, uPrime

def main( args, debug = False):
    #parse the command line arguments for include and exclude files
    
    includeFiles, excludeFiles, crossValidate, cleanup, verbose, eprimerOptions, lf, uPrimer, fastaDiff = parseArgs( args ) ##Mau add: lf
    utils.initialize( True, cleanup, lf)  ##Mau: add lf
    #find primers for the include sequences
   
    tmpdir = utils.getTemporaryDirectory() ## added by Alexis
    command = "cp -rf " + tmpdir + "/sequenceForEprimer.fasta" + " " + fastaDiff
 
    try:
        utils.logMessage( "uniqprimer::Main( )", "Logging include files: " )
        utils.logList( "uniqprimer::Main( )", includeFiles )
        utils.logMessage( "uniqprimer::Main( )", "Logging exclude files: " ) 
        utils.logList( "uniqprimer::Main( )", excludeFiles)
        print "*** Finding Primers ***"
        uniqPrimer = UniqPrimerFinder( includeFiles, excludeFiles, crossValidate, eprimerOptions) 
        uniqPrimer.findPrimers( )
    except utils.NoFileFoundException as nfe:
        print "File not found: " + str( nfe.filename )
        printUsageAndQuit( )
    except utils.ProgramNotFoundException as pnfe:
        print str( pnfe.programName ) + ": program is not installed or is not in your path."
        print str( pnfe.details )
    except utils.NoPrimersExistException as npe:
        print "Failure: No unique primers exist for this combination"
    except exceptions.BaseException as e:
        print "It appears that an unknown sequence of events has resulted in the internal explosion of this program. Please send the file called \'log_uniqprimer.txt\' to herndon@cs.colostate.edu and tell that bonehead John to fix it!"
        print "Details:"
        print e    
    
    os.system("cp -rf " + tmpdir + "/sequenceForEprimer.fasta" + " " + fastaDiff)
    utils.shutdown( )

    print "*** Finished ***"
    
if __name__ == '__main__':
    
    #temp_args = "-i data/testdata/smallinclude.ffn -x data/testdata/smallexclude.ffn".split( )
    
    #temp_args = "-i data/XOO_MAI1_scaffolds.fas -x data/KACC.ffn".split( )
    if len( sys.argv ) == 1:
        printUsageAndQuit( )
    main( sys.argv[ 1: ], debug = True )
    
    
    
    
    
    
    
    
    
    
    
    
    
