'''
Created on Jan 1, 2011

@author: John L. Herndon
@contact: herndon@cs.colostate.edu
@organization: Colorado State University
@group: Computer Science Department, Asa Ben-Hur's laboratory 
'''

import utils

class PrimerSequence( object ):
    """
    record sequence data, and store matched parts of the sequence 
    """
    
    def __init__( self, seqID, seqLength, sequence ):
        #an unmatched sub-sequence that starts at 0 goes until the end of the the sequence, to start out with.
        
        self.seqID = seqID
        self.seqLength = seqLength
        self.matchedSubSequences = [ ] 
        self.sequence = sequence
        
    def addMatch( self, match ):
        """
        Input: a utils.Match object
        Removes the matched sequence from the list of valid sequence data
        """
        
        self.matchedSubSequences.append( ( match.start, match.end ) )
    
    def findNonMatchedIndices( self ):
        
        utils.logMessage("PrimerSequence::findValidIndices( )", "getting unmatched sequence indices" )

        sequence = set( range( self.seqLength ) )
        
        #find the indices that are NOT excluded
        utils.logMessage( "PrimerSequence::findValidIndices( )", "there are {0} excluded sequences for {1}".format( len( self.matchedSubSequences ), self.seqID ) )
        for exclude in self.matchedSubSequences:
            excludedSequence = set( range( exclude[ 0 ], exclude[ 1 ] )  )
            utils.logMessage("PrimerSequence::findValidIndices( )", "removing exclude sequence {0} - {1}".format( exclude[ 0 ], exclude[ 1 ] ) )
            sequence = sequence - excludedSequence

        utils.logMessage("PrimerSequence::findValidIndices( )", "{0} unique indices".format( len( sequence ) ) )
            
        return list( sequence )
    
    def findNonMatchedIndexSequences( self, indices ):
        
        utils.logMessage("PrimerSequence::findValidIndexSequences( )", "getting sequences from unique indices" )
        
        sequences = [ ]
        curSeq = [ ]
        for index in indices:
            if len( curSeq ) == 0:
                curSeq.append( index )
            elif index == curSeq[ -1 ] + 1:
                curSeq.append( index )
            else:
                sequences.append( curSeq )
                curSeq = [ ]
        sequences.append( curSeq )        
        utils.logMessage("PrimerSequence::findValidIndexSequences( )", "{0} sequences found".format( len( sequences ) ) )        
        
        return sequences
    
    
    def getNonMatchedSubSequences( self, minLength = 100 ):
        """
        Get all valid sub sequences after removing matches
        """        

        utils.logMessage("PrimerSequence::getNonMatchedSubSequences( )", "finding valid sub sequences for {0}".format( self.seqID ) )

        indices = self.findNonMatchedIndices( ) 
        indexSequences = self.findNonMatchedIndexSequences( indices )
        
        subSequences = [ ]
        
        for indexSequence in indexSequences:
            subSequence = [ self.sequence[ i ] for i in indexSequence ]
            
            if len( subSequence ) >= minLength:
                subSequences.append( subSequence )
        
        return subSequences
    
    def getMatchedSubSequences( self, minLength = 100 ):
        utils.logMessage("PrimerSequence::getMatchedSubSequences( )", "finding valid sub sequences for {0}".format( self.seqID ) )
        
        returnValue = [ ]
        for match in self.matchedSubSequences:
            subSequence = self.sequence[ match[ 0 ]:match[ 1 ] ]
            
            if len( subSequence ) >= minLength :
                returnValue.append( subSequence )
            
        return returnValue
            
                
         
        
        
        
        
        
        
    