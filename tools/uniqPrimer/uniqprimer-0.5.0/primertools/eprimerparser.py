'''
Created on Jan 1, 2011

@author: John L. Herndon
@contact: herndon@cs.colostate.edu
@organization: Colorado State University
@group: Computer Science Department, Asa Ben-Hur's laboratory 
'''

import os
import utils
import re

def parsePrimerSequences( eprimerFile ):
    '''
    parse an eprimer3 output file for all primers
    '''
    
    utils.logMessage( "eprimerparser::parsePrimerSequences( )", "parsing for primer sequences" )
    if os.path.exists( eprimerFile ) == False:
        utils.logMessage( "eprimerparser::parsePrimerSequences( )", "ERROR - eprimer file was not found" )
        raise utils.NoFileFoundException( eprimerFile )
    
    
    primers = [ ]
    primerFile = open( eprimerFile )
    
    currentPrimer = None
            
    nextPrimerId = 0
    for line in primerFile.readlines( ):
        
        if line[ 0 ] == '# ':
            continue
        
        if line.find( "PRODUCT SIZE" ) != -1:
            if currentPrimer is not None:
                primers.append( currentPrimer )
            currentPrimer = utils.PrimerSet( str( nextPrimerId ) )
            nextPrimerId += 1
            productSize = int( line.split( ':' )[ 1 ].strip( ) )
            currentPrimer.setProductSize( productSize )
        else:
            tokens = re.split( ' *', line.strip( ) ) 
            if len( tokens ) == 7:
                
                sequence = tokens[ 6 ]
                temp = tokens[ 4 ]
            
                if tokens[ 0 ] == "FORWARD": 
                    currentPrimer.setForwardPrimerData( sequence, temp )
                elif tokens[ 0 ] == "REVERSE":
                    currentPrimer.setReversePrimerData( sequence, temp )
    
    if currentPrimer is not None:
        primers.append( currentPrimer )
    
    utils.logMessage( "eprimerparser::parsePrimerSequences( )", "finished parsing. found {0} primers".format( len( primers ) ) )
    return primers        
                
            
        
        
        
        
        
        
        
        
        
        
    
    
     
    