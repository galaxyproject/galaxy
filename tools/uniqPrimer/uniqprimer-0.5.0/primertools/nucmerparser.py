'''
Created on Jan 1, 2011

@author: John L. Herndon
@contact: herndon@cs.colostate.edu
@organization: Colorado State University
@group: Computer Science Department, Asa Ben-Hur's laboratory 
'''

import utils
import os
import re

def parseCoordMatchLine( match ):
      
    match = match.replace( '\t', ' ' )
    sections = match.split( '|', 4 )
        
    #parse the first section, containing the start and end
    #locations of the match
    firstsection = sections[ 0 ].strip( )
    firstsectiontokens = re.split( ' +', firstsection )
    start = int( firstsectiontokens[ 0 ].strip( ) )
    end = int( firstsectiontokens[ 1 ].strip( ) )
    
    #parse the last section, containing the sequenceID
    lastsection = sections[ -1 ].strip( )
    lastsectiontokens = re.split( " +", lastsection )
        
    seqid = lastsectiontokens[ 0 ].strip( )
    
    return utils.Match( start, end, seqid )
        
def parseCoordMatchFile( coordFileName ):
    '''
    A method to parse the coord file.
    returns a list of utils.match objects
    '''
    returnValue = [ ]
    
    #throw if the file doesn't exist
    if os.path.exists( coordFileName ) == False:
        raise utils.NoFileFoundException( coordFileName )
    
    
    #read the nucmer file into memory
    lines = open( coordFileName ).readlines( )
    
    #skip forward to the start of the matches. 
    i = 0
    while lines[ i ] [ 0] != '=':
        i += 1
    matchLines = lines[ i+1 : ]
    
    #parse each line for match start, end and sequenceID
    for matchLine in matchLines:
        returnValue.append( parseCoordMatchLine( matchLine ) )
    
    utils.logMessage( "NucmerParser::parseCoordMatchFile( )", "Parse {0}, finding {1} matches".format( coordFileName, len( returnValue ) ) )

    return returnValue
    
        
        
        
        
        
        