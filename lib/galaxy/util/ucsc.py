"""
Utilities for dealing with UCSC data.
"""


class UCSCLimitException( Exception ):
    pass


class UCSCOutWrapper( object ):
    """File-like object that throws an exception if it encounters the UCSC limit error lines"""
    def __init__( self, other ):
        self.other = iter( other )
        # Need one line of lookahead to be sure we are hitting the limit message
        self.lookahead = None

    def __iter__( self ):
        return self

    def next( self ):
        if self.lookahead is None:
            line = self.other.next()
        else:
            line = self.lookahead
            self.lookahead = None
        if line.startswith( "----------" ):
            next_line = self.other.next()
            if next_line.startswith( "Reached output limit" ):
                raise UCSCLimitException( next_line.strip() )
            else:
                self.lookahead = next_line
        return line

    def readline(self):
        return self.next()
