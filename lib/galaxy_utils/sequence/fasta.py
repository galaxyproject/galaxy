# Dan Blankenberg
from six import string_types


class fastaSequence( object ):
    def __init__( self ):
        self.identifier = None
        self.sequence = ''  # holds raw sequence string: no whitespace

    def __len__( self ):
        return len( self.sequence )

    def __str__( self ):
        return "%s\n%s\n" % ( self.identifier, self.sequence )


class fastaReader( object ):
    def __init__( self, fh ):
        self.file = fh

    def close( self ):
        return self.file.close()

    def next( self ):
        line = self.file.readline()
        # remove header comment lines
        while line and line.startswith( '#' ):
            line = self.file.readline()
        if not line:
            raise StopIteration
        assert line.startswith( '>' ), "FASTA headers must start with >"
        rval = fastaSequence()
        rval.identifier = line.strip()
        offset = self.file.tell()
        while True:
            line = self.file.readline()
            if not line or line.startswith( '>' ):
                if line:
                    self.file.seek( offset )  # this causes sequence id lines to be read twice, once to determine previous sequence end and again when getting actual sequence; can we cache this to prevent it from being re-read?
                return rval
            # 454 qual test data that was used has decimal scores that don't have trailing spaces
            # so we'll need to parse and build these sequences not based upon de facto standards
            # i.e. in a less than ideal fashion
            line = line.rstrip()
            if ' ' in rval.sequence or ' ' in line:
                rval.sequence = "%s%s " % ( rval.sequence, line )
            else:
                rval.sequence += line
            offset = self.file.tell()

    def __iter__( self ):
        while True:
            yield self.next()


class fastaNamedReader( object ):
    def __init__( self, fh ):
        self.file = fh
        self.reader = fastaReader( self.file )
        self.offset_dict = {}
        self.eof = False

    def close( self ):
        return self.file.close()

    def get( self, sequence_id ):
        if not isinstance( sequence_id, string_types ):
            sequence_id = sequence_id.identifier
        rval = None
        if sequence_id in self.offset_dict:
            initial_offset = self.file.tell()
            seq_offset = self.offset_dict[ sequence_id ].pop( 0 )
            if not self.offset_dict[ sequence_id ]:
                del self.offset_dict[ sequence_id ]
            self.file.seek( seq_offset )
            rval = self.reader.next()
            self.file.seek( initial_offset )
        else:
            while True:
                offset = self.file.tell()
                try:
                    fasta_seq = self.reader.next()
                except StopIteration:
                    self.eof = True
                    break  # eof, id not found, will return None
                if fasta_seq.identifier == sequence_id:
                    rval = fasta_seq
                    break
                else:
                    if fasta_seq.identifier not in self.offset_dict:
                        self.offset_dict[ fasta_seq.identifier ] = []
                    self.offset_dict[ fasta_seq.identifier ].append( offset )
        return rval

    def has_data( self ):
        # returns a string representation of remaining data, or empty string (False) if no data remaining
        eof = self.eof
        count = 0
        rval = ''
        if self.offset_dict:
            count = sum( map( len, self.offset_dict.values() ) )
        if not eof:
            offset = self.file.tell()
            try:
                self.reader.next()
            except StopIteration:
                eof = True
            self.file.seek( offset )
        if count:
            rval = "There were %i known sequences not utilized. " % count
        if not eof:
            rval = "%s%s" % ( rval, "An additional unknown number of sequences exist in the input that were not utilized." )
        return rval


class fastaWriter( object ):
    def __init__( self, fh ):
        self.file = fh

    def write( self, fastq_read ):
        # this will include color space adapter base if applicable
        self.file.write( ">%s\n%s\n" % ( fastq_read.identifier[1:], fastq_read.sequence ) )

    def close( self ):
        return self.file.close()
