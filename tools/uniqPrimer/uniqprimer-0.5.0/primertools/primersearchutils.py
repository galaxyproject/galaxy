'''
Created on Jan 1, 2011

@author: John L. Herndon
@contact: herndon@cs.colostate.edu
@organization: Colorado State University
@group: Computer Science Department, Asa Ben-Hur's laboratory 
'''

import utils

def writePrimerSearchInputFile( primerSets, outputFile ):
    '''
    A function to write primer pairs to a file formatted as primer search input.
    primerPairs - a list of utils.PrimerSet objects
    outputFile - a string containing the path to the output file
    '''
    
    file = open( outputFile, 'w' )
    i = 0
    for primerSet in primerSets:
        i += 1
        if primerSet.reversePrimer == "":
            print "Error - primer {0} has no reverse primer. {1} primers total".format( i, len( primerSets ) )
            continue
        file.write( primerSet.id + "\t" + primerSet.forwardPrimer + "\t" + primerSet.reversePrimer + "\n" )
        
    file.close( )
    
def parsePrimerSearchFile( primerSearchFileName ):
    '''
    return a list of primer ids that are associated with at least one amplimer in the primer search output file.
    '''
    found = [ ]
    
    amplimerFound = False
    currentId = -1;
    for line in open( primerSearchFileName ).readlines( ):
        
        if "Primer name" in line:
            #the id of the primer is found after the string "Primer name" in the file
            currentId = line.split( ' ' )[ 2: ][ 0 ].strip( )
        elif "Amplimer" in line and currentId not in found:
            found.append( currentId )
                
    if amplimerFound == True:
        found.append( currentId )   
    
    return found
            
            
        
        
    
    