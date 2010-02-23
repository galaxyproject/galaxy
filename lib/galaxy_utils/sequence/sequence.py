#Dan Blankenberg
import transform
import string
from copy import deepcopy

class SequencingRead( object ):
    color_space_converter = transform.ColorSpaceConverter()
    valid_sequence_list = string.letters
    def __init__( self ):
        self.identifier = None
        self.sequence = '' #holds raw sequence string: no whitespace
        self.description = None
        self.quality = '' #holds raw quality string: no whitespace, unless this contains decimal scores
    def __len__( self ):
        return len( self.sequence )
    def __str__( self ):
        return "%s\n%s\n%s\n%s\n" % ( self.identifier, self.sequence, self.description, self.quality )
    def append_sequence( self, sequence ):
        self.sequence += sequence.rstrip( '\n\r' )
    def append_quality( self, quality ):
        self.quality += quality.rstrip( '\n\r' )
    def is_DNA( self ):
        return 'u' not in self.sequence.lower()
    def clone( self ):
        return deepcopy( self )
    def reverse( self, clone = True ):
        if clone:
            rval = self.clone()
        else:
            rval = self
        rval.sequence = transform.reverse( self.sequence )
        rval.quality = rval.quality[::-1]
        return rval
    def complement( self, clone = True ):
        if clone:
            rval = self.clone()
        else:
            rval = self
        if rval.is_DNA():
            rval.sequence = transform.DNA_complement( rval.sequence )
        else:
            rval.sequence = transform.RNA_complement( rval.sequence )
        return rval
    def reverse_complement( self, clone = True ):
        #need to reverse first, then complement
        rval = self.reverse( clone = clone )
        return rval.complement( clone = False ) #already working with a clone if requested
    def sequence_as_DNA( self, clone = True ):
        if clone:
            rval = self.clone()
        else:
            rval = self
        rval.sequence = transform.to_DNA( rval.sequence )
        return rval
    def sequence_as_RNA( self, clone = True ):
        if clone:
            rval = self.clone()
        else:
            rval = self
        rval.sequence = transform.to_RNA( rval.sequence )
        return rval
