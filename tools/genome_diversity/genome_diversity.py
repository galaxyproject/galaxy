#!/usr/bin/env python2.5

import cdblib

def _openfile( filename=None, mode='r' ):
    try:
        fh = open( filename, mode )
    except IOError, err:
        raise RuntimeError( "can't open file: %s\n" % str( err ) )
    return fh

def get_filename_from_loc( species=None, filename=None ):
    fh = _openfile( filename )
    for line in fh:
        if line and not line.startswith( '#' ):
            line = line.rstrip( '\r\n' )
            if line:
                elems = line.split( '\t' )
                if len( elems ) >= 2 and elems[0] == species:
                    return elems[1]
    return None


class SnpFile:
    def __init__( self, filename=None, seq_col=1, pos_col=2, ref_seq_col=7, ref_pos_col=8 ):
        self.filename = filename
        self.fh = _openfile( filename )
        self.seq_col = seq_col
        self.pos_col = pos_col
        self.ref_seq_col = ref_seq_col
        self.ref_pos_col = ref_pos_col
        self.elems = None
        self.line = None

    def next( self ):
        while self.fh:
            try:
                self.line = self.fh.next()
            except StopIteration:
                self.line = None
                self.elems = None
                return None
            if self.line and not self.line.startswith( '#' ):
                self.line = self.line.rstrip( '\r\n' )
                if self.line:
                    self.elems = self.line.split( '\t' )
                    return 1

    def get_seq_pos( self ):
        if self.elems:
            return self.elems[ self.seq_col - 1 ], self.elems[ self.pos_col - 1 ]
        else:
            return None, None

    def get_ref_seq_pos( self ):
        if self.elems:
            return self.elems[ self.ref_seq_seq - 1 ], self.elems[ self.ref_pos_col - 1 ]
        else:
            return None, None


class IndexedFile:

    def __init__( self, data_file=None, index_file=None ):
        self.data_file = data_file
        self.index_file = index_file
        self.data_fh = _openfile( data_file )
        self.index_fh = _openfile( index_file )
        self._reader = cdblib.Reader( self.index_fh.read(), hash )

    def get_indexed_line( self, key=None ):
        line = None
        if key in self._reader:
            offset = self._reader.getint( key )
            self.data_fh.seek( offset )
            try:
                line = self.data_fh.next()
            except StopIteration:
                raise RuntimeError( 'index file out of sync for %s' % key )
        return line

class PrimersFile( IndexedFile ):
    def get_primer_header( self, sequence=None, position=None ):
        key = "%s %s" % ( str( sequence ), str( position ) )
        header = self.get_indexed_line( key )
        if header:
            if header.startswith( '>' ):
                elems = header.split()
                if len( elems ) < 3:
                    raise RuntimeError( 'short primers header for %s' % key )
                if sequence != elems[1] or str( position ) != elems[2]:
                    raise RuntimeError( 'primers index for %s finds %s %s' % ( key, elems[1], elems[2] ) )
            else:
                raise RuntimeError( 'primers index out of sync for %s' % key )
        return header

    def get_entry( self, sequence=None, position=None ):
        entry = self.get_primer_header( sequence, position )
        if entry:
            while self.data_fh:
                try:
                    line = self.data_fh.next()
                except StopIteration:
                    break
                if line.startswith( '>' ):
                    break
                entry += line
        return entry

    def get_enzymes( self, sequence=None, position=None ):
        entry = self.get_primer_header( sequence, position )
        enzyme_list = []
        if entry:
            try:
                line = self.data_fh.next()
            except StopIteration:
                raise RuntimeError( 'primers entry for %s %s is truncated' % ( str( sequence ), str( position ) ) )
            if line.startswith( '>' ):
                raise RuntimeError( 'primers entry for %s %s is truncated' % ( str( sequence ), str( position ) ) )
            line.rstrip( '\r\n' )
            if line:
                enzymes = line.split( ',' )
                for enzyme in enzymes:
                    enzyme = enzyme.strip()
                    if enzyme:
                        enzyme_list.append( enzyme )
        return enzyme_list

class SnpcallsFile( IndexedFile ):
    def get_snp_seq( self, sequence=None, position=None ):
        key = "%s %s" % ( str( sequence ), str( position ) )
        line = self.get_indexed_line( key )
        if line:
            elems = line.split( '\t' )
            if len (elems) < 3:
                raise RuntimeError( 'short snpcalls line for %s' % key )
            if sequence != elems[0] or str( position ) != elems[1]:
                raise RuntimeError( 'snpcalls index for %s finds %s %s' % ( key, elems[0], elems[1] ) )
            return elems[2]
        else:
            return None

    def get_flanking_dna( self, sequence=None, position=None, format='fasta' ):
        if format != 'fasta' and format != 'primer3':
            raise RuntimeError( 'invalid format for flanking dna: %s' % str( format ) )
        seq = self.get_snp_seq( sequence, position )
        if seq:
            p = seq.find('[')
            if p == -1:
                raise RuntimeError( 'snpcalls entry for %s %s missing left bracket: %s' % ( str( sequence ), str( position ), seq ) )
            q = seq.find(']', p + 1)
            if q == -1:
                raise RuntimeError( 'snpcalls entry for %s %s missing right bracket: %s' % ( str( sequence ), str( position ), seq ) )
            q += 1

            if format == 'fasta':
                flanking_seq = '> '
            else:
                flanking_seq = 'SEQUENCE_ID='

            flanking_seq += "%s %s %s %s\n" % ( str( sequence ), str( position ), seq[p+1], seq[p+3] )

            if format == 'primer3':
                flanking_seq += 'SEQUENCE_TEMPLATE='

            flanking_seq += "%sn%s\n" % ( seq[0:p], seq[q:] )

            if format == 'primer3':
                flanking_seq += "SEQUENCE_TARGET=%d,11\n=\n" % ( p - 5 )

            return flanking_seq
        else:
            return None

