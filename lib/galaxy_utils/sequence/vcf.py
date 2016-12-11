# Dan Blankenberg
# See http://www.1000genomes.org/wiki/Analysis/variant-call-format

NOT_A_NUMBER = float( 'NaN' )


class VariantCall( object ):
    version = None
    header_startswith = None
    required_header_fields = None
    required_header_length = None

    @classmethod
    def get_class_by_format( cls, format ):
        assert format in VCF_FORMATS, 'Unknown format type specified: %s' % format
        return VCF_FORMATS[ format ]

    def __init__( self, vcf_line, metadata, sample_names ):
        raise Exception( 'Abstract Method' )


class VariantCall33( VariantCall ):
    version = 'VCFv3.3'
    header_startswith = '#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO'
    required_header_fields = header_startswith.split( '\t' )
    required_header_length = len( required_header_fields )

    def __init__( self, vcf_line, metadata, sample_names ):
        # Raw line is needed for indexing file.
        self.raw_line = vcf_line
        self.line = vcf_line.rstrip( '\n\r' )
        self.metadata = metadata
        self.sample_names = sample_names
        self.format = None
        self.sample_values = []

        # parse line
        self.fields = self.line.split( '\t' )
        if sample_names:
            assert len( self.fields ) == self.required_header_length + len( sample_names ) + 1, 'Provided VCF line (%s) has wrong length (expected: %i)' % ( self.line, self.required_header_length + len( sample_names ) + 1 )
        else:
            assert len( self.fields ) == self.required_header_length, 'Provided VCF line (%s) has wrong length (expected: %i)' % ( self.line, self.required_header_length)
        self.chrom, self.pos, self.id, self.ref, self.alt, self.qual, self.filter, self.info = self.fields[ :self.required_header_length ]
        self.pos = int( self.pos )
        self.alt = self.alt.split( ',' )
        try:
            self.qual = float( self.qual )
        except:
            self.qual = NOT_A_NUMBER  # Missing data can be denoted as a '.'
        if len( self.fields ) > self.required_header_length:
            self.format = self.fields[ self.required_header_length ].split( ':' )
            for sample_value in self.fields[ self.required_header_length + 1: ]:
                self.sample_values.append( sample_value.split( ':' ) )


class VariantCall40( VariantCall33 ):
    version = 'VCFv4.0'

    def __init__( self, vcf_line, metadata, sample_names ):
        VariantCall33.__init__( self, vcf_line, metadata, sample_names)


class VariantCall41( VariantCall40 ):
    version = 'VCFv4.1'


# VCF Format version lookup dict
VCF_FORMATS = {}
for format in [ VariantCall33, VariantCall40, VariantCall41 ]:
    VCF_FORMATS[format.version] = format


class Reader( object ):
    def __init__( self, fh ):
        self.vcf_file = fh
        self.metadata = {}
        self.header_fields = None
        self.metadata_len = 0
        self.sample_names = []
        self.vcf_class = None

        # Read file metadata.
        while True:
            line = self.vcf_file.readline()
            self.metadata_len += len( line )
            assert line, 'Invalid VCF file provided.'
            line = line.rstrip( '\r\n' )
            if self.vcf_class and line.startswith( self.vcf_class.header_startswith ):
                # read the header fields, ignoring any blank tabs, which GATK
                # VCF produces after the sample
                self.header_fields = [l for l in line.split( '\t' ) if l]
                if len( self.header_fields ) > self.vcf_class.required_header_length:
                    for sample_name in self.header_fields[ self.vcf_class.required_header_length + 1: ]:
                        self.sample_names.append( sample_name )
                break
            assert line.startswith( '##' ), 'Non-metadata line found before header'
            line = line[2:]  # strip ##
            metadata = line.split( '=', 1 )
            metadata_name = metadata[ 0 ]
            if len( metadata ) == 2:
                metadata_value = metadata[ 1 ]
            else:
                metadata_value = None
            if metadata_name in self.metadata:
                if not isinstance( self.metadata[ metadata_name ], list ):
                    self.metadata[ metadata_name ] = [ self.metadata[ metadata_name ] ]
                self.metadata[ metadata_name ].append( metadata_value )
            else:
                self.metadata[ metadata_name ] = metadata_value
            if metadata_name == 'fileformat':
                self.vcf_class = VariantCall.get_class_by_format( metadata_value )

    def next( self ):
        line = self.vcf_file.readline()
        if not line:
            raise StopIteration
        return self.vcf_class( line, self.metadata, self.sample_names )

    def __iter__( self ):
        while True:
            yield self.next()
