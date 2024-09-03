'''
Created on Jan 1, 2011

@author: John L. Herndon
@contact: herndon@cs.colostate.edu
@organization: Colorado State University
@group: Computer Science Department, Asa Ben-Hur's laboratory 
'''


import utils
import primersequence

from Bio import SeqIO
from Bio import Seq
from Bio import Alphabet

def parseFastaFileAsPrimerSequence( fileName ):
    
    utils.logMessage("fastaparser::parseFastaFileAsPrimerSequence( )", "parsing fasta file {0}".format( fileName ) )
    returnValue = { }
    
    sequences = SeqIO.parse( open( fileName ), "fasta" )
    
    for sequence in sequences:
        seqdata = primersequence.PrimerSequence( sequence.id, len( sequence ), sequence.seq )
        returnValue[ sequence.id ] = seqdata
    
    utils.logMessage("fastaparser::parseFastaFileAsPrimerSequence( )", "read {0} sequences".format( len( returnValue.keys( ) ) ) )
    
    return returnValue
    
def parseFastaFile( fileName ):
    '''
    parse a fasta file and return a list of Bio.Seq
    '''
    utils.logMessage("fastaparser::parseFastaFile( )", "parsing fasta file {0}".format( fileName ) )
    
    sequences =  SeqIO.parse( open( fileName ), "fasta" )
    
    return sequences

def writeFastaFile( sequences, fileName ):
    '''
    write a set of sequences to a fasta file.
    returns the name of the new file
    ''' 
    
    primerSequenceIdent = "primer_sequences"
    utils.logMessage( "PrimerManager::writeFastaFile( )", "Writing {0} sequences to fasta file".format( len( sequences ) ) )
    seqRecords = [ ]
    i = 0
    for sequence in sequences:
        seqStr = str( reduce( lambda x, y: str( x )+str( y ), sequence) )
        seqRecord = SeqIO.SeqRecord( Seq.Seq( seqStr, Alphabet.IUPAC.extended_dna ),  id="seq_{0}".format( i ) )
        seqRecords.append( seqRecord )
        i += 1

    SeqIO.write( seqRecords, open( fileName, "w" ), "fasta" )
        
    utils.logMessage( "PrimerManager::writeFastaFile( )", "writing fasta file complete" )    
    return fileName
        