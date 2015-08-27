"""
"""
import struct
import math

from galaxy.datatypes.dataproviders import base

import logging
log = logging.getLogger( __name__ )


# -----------------------------------------------------------------------------
class MrhSquareDataProvider( base.LimitedOffsetDataProvider ):
    """
    """
    settings = {
        'chrom1'         : 'str',
        'start1'         : 'float',
        'stop1'          : 'float',
        'chrom2'         : 'str',
        'start2'         : 'float',
        'stop2'          : 'float',
        'minresolution'  : 'float',
        'maxresolution'  : 'float',
        'header'         : 'bool',
        'chromosomes'    : 'bool',
    }

    def __init__( self, source, **kwargs ):
        """
        :param chrom1: chromosome for sequence1
        :type chrom1: str.

        :param start1: starting bp in sequence 1
        :type start1: long

        :param stop1: stopping bp in sequence 1
        :type stop1: long

        :param chrom2: chromosome for sequence2
        :type chrom2: str.

        :param start2: starting bp in sequence 2
        :type start2: long

        :param stop2: stopping bp in sequence 2
        :type stop2: long

        :param minresolution: largest bin size to return
        :type minresolution: long

        :param maxresolution: smallest bin size to return
        :type maxresolution: long

        :param header: T/F send chromosome-specific header data instead
        :type resolution: bool

        :param chromosomes: T/F send chromosome list instead
        :type resolution: bool
        """
        super( MrhSquareDataProvider, self ).__init__( source, **kwargs )
        self.chroms_only, self.header_only = False, False
        self.chrom1, self.chrom2 = '', ''
        self.start1, self.stop1, self.start2, self.stop2 = 0, 0, 0, 0
        self.minresolution, self.maxresolution, self.window1, self.window2 = 0, 0, 0, 0
        if 'chromosomes' in kwargs and kwargs['chromosomes']:
            self.chroms_only = True
        else:
            if 'header' in kwargs and kwargs['header']:
                self.header_only = True
        if not self.chroms_only:
            for key in [ 'chrom1', 'chrom2' ]:
                if key in kwargs:
                    self[ key ] = kwargs[ key ].strip( 'chr' )
        if not self.header_only:
            for key in [ 'start1', 'start2', 'stop1', 'stop2', 'minresolution', 'maxresolution' ]:
                if key in kwargs:
                    self[ key ] = int( round( float( kwargs[ key ] ) ) )
            if self.minresolution != self.maxresolution:
                self.levels = {}
                i = self.minresolution
                j = 0
                while i >= self.maxresolution:
                    self.levels[i] = j
                    i /= 2
                    j += 1
            else:
                self.levels = { self.maxresolution: 0 }
            if self.chrom1 == self.chrom2 and (self.stop1 > self.start2 and self.stop2 > self.start1):
                self.overlap = True
            else:
                self.overlap = False
            self.window1 = self.stop1 - self.start1
            self.window2 = self.stop2 - self.start2
        self.header = None

    def __getitem__(self, key):
        """Dictionary-like lookup."""
        if key in self.__dict__:
            return self.__dict__[key]
        else:
            return None

    def __setitem__(self, key, value):
        """Dictionary-like value setting."""
        self.__dict__[key] = value
        return None

    def __iter__( self ):
        with self.source as infile:
            if self.chroms_only:
                yield self.load_chrom_data( infile )
            elif self.header_only:
                header = self.load_header( infile )
                if self.transpose:
                    header['start1'], header['start2'] = header['start2'], header['start1']
                    header['stop1'], header['stop2'] = header['stop2'], header['stop1']
                    header['m'], header['n'] = header['n'], header['m']
                yield header
            elif self.chrom1 != '' and self.chrom2 != '':
                if self.header is None:
                    self.load_header( infile )
                if self.transpose:
                    self.start1, self.start2 = self.start2, self.start1
                    self.stop1, self.stop2 = self.stop2, self.stop1
                    self.window1, self.window2 = self.window2, self.window1
                if self.chrom1 != self.chrom2:
                    for square in self.paint_trans_canvas( infile ):
                        yield self.interpolate_square( square )
                else:
                    for square in self.paint_cis_canvas( infile ):
                        yield self.interpolate_square( square )

    def load_chrom_data( self, infile ):
        """
        """
        self.header = {}
        # get and validate magic number for mrh type
        mrh_magic_number = '42054205'
        mrh_magic_number_size = 4
        infile.seek( 0 )
        magic_number = ''.join( c.encode( 'hex' ) for c in infile.read( mrh_magic_number_size ).replace( '\\x', '' ) )
        if magic_number != mrh_magic_number:
            raise TypeError( 'File does not appear to be a multi-resolution heatmap file' )

        # get the number of chromosomes and whether the file includes inter-chromosome maps
        int_float32_size = 4
        trans, num_chroms = struct.unpack( '>ii', infile.read( int_float32_size * 2 ) )
        self.trans = trans
        self.num_chroms = num_chroms
        name_sizes = struct.unpack( '>' + 'i' * num_chroms, infile.read( int_float32_size * num_chroms ) )

        # create dictionary of chromosome names and indices, retrieve chrom indices for requested data
        self.chr2int = {}
        for i in range( num_chroms ):
            self.chr2int[ ''.join( struct.unpack( '>' + 'c' * name_sizes[i],
                infile.read( name_sizes[i] ) ) ).strip( ) ] = i
        return { 'chromosomes': self.chr2int.keys( ), 'includes_trans': bool( trans ) }

    def load_header( self, infile ):
        int_float32_size = 4
        short_size = 2
        self.load_chrom_data( infile )
        trans = self.trans
        num_chroms = self.num_chroms
        if self.chrom1 != self.chrom2 and not trans:
            raise TypeError( 'File does not appear to contain inter-chromosome data' )
        if trans:
            num_pairings = ( num_chroms * ( num_chroms + 1 ) ) / 2
        else:
            num_pairings = num_chroms
        if self.chrom1 in self.chr2int and self.chrom2 in self.chr2int:
            chr_index1 = self.chr2int[ self.chrom1 ]
            chr_index2 = self.chr2int[ self.chrom2 ]
        else:
            raise KeyError( 'File does not appear to contain data for the requested chromosome(s)' )
        self.transpose = False
        if trans:
            if chr_index1 > chr_index2:
                self.transpose = True
                chr_index1, chr_index2 = chr_index2, chr_index1
            pairing_index = chr_index1 * ( num_chroms - 1 ) - ( chr_index1 * ( chr_index1 - 1 ) ) / 2 + chr_index2
        else:
            pairing_index = chr_index1

        # get index of chrom/chrom-pair data starting byte and ending byte
        infile.seek( pairing_index * int_float32_size, 1 )
        start_index, stop_index = struct.unpack( '>' + 'i' * 2, infile.read( int_float32_size * 2 ) )
        self.header[ 'offset' ] = start_index
        self.header[ 'total_bytes' ] = stop_index - start_index
        skip = num_pairings - pairing_index - 1

        # get number of top-layer partitions
        if chr_index1 != chr_index2:
            # skip intra-chromosomal partitions and find inter-chromosome partitions for requested chroms
            infile.seek( ( skip + chr_index1 + num_chroms ) * int_float32_size, 1 )
            self.header[ 'n' ] = struct.unpack( '>i', infile.read( int_float32_size ) )[0]
            infile.seek( ( chr_index2 - chr_index1 - 1 ) * int_float32_size, 1 )
            self.header[ 'm' ] = struct.unpack( '>i', infile.read( int_float32_size ) )[0]
            skip = num_chroms - chr_index2 - 1
        else:
            # find intra-chromosome partitions for requested chrom
            infile.seek( ( skip + chr_index1 ) * int_float32_size, 1 )
            self.header[ 'n' ] = struct.unpack( '>i', infile.read( int_float32_size ) )[0]
            if trans:
                # skip inter-chromosomal paritions
                skip = num_chroms * 2 - chr_index1 - 1
            else:
                skip = num_chroms - chr_index1 - 1

        # get total number of data bins for chrom/chrom-pair
        infile.seek( ( skip + pairing_index ) * int_float32_size, 1 )
        self.header[ 'data_bins' ] = struct.unpack( '>i', infile.read( int_float32_size ) )[0]
        skip = num_pairings - pairing_index - 1

        # get total number of index bins for chrom/chrom-pair
        infile.seek( ( skip + pairing_index ) * int_float32_size, 1 )
        self.header[ 'index_bins' ] = struct.unpack( '>i', infile.read( int_float32_size ) )[0]
        self.header[ 'shape_bins' ] = ( self.header[ 'total_bytes' ] - ( self.header[ 'data_bins' ] +
                                        self.header[ 'index_bins' ] ) * int_float32_size ) / short_size
        self.header[ 'total_bins' ] = ( self.header[ 'index_bins' ] + self.header[ 'data_bins' ] +
                                        self.header[ 'shape_bins' ] )
        skip = num_pairings - pairing_index - 1

        # get starting coordinate(s)
        if chr_index1 != chr_index2:
            # skip intra-chromosomal start coordinates and find inter-chromosome start coordinates for requested chroms
            infile.seek( ( skip + num_chroms + chr_index1 ) * int_float32_size, 1 )
            self.header[ 'start1' ] = struct.unpack( '>i', infile.read( int_float32_size ) )[0]
            infile.seek( ( chr_index2 - chr_index1 - 1 ) * int_float32_size, 1 )
            self.header[ 'start2' ] = struct.unpack( '>i', infile.read( int_float32_size ) )[0]
            skip = num_chroms - chr_index2 - 1
        else:
            # find intra-chromosome start coordinate for requested chrom
            infile.seek( ( skip + chr_index1 ) * int_float32_size, 1 )
            self.header[ 'start' ] = struct.unpack( '>i', infile.read( int_float32_size ) )[0]
            if trans:
                # skip inter-chromosomal start coordinates
                skip = num_chroms * 2 - chr_index1 - 1
            else:
                skip = num_chroms - chr_index1 - 1

        # get stopping coordinate(s)
        if chr_index1 != chr_index2:
            # skip intra-chromosomal stop coordinates and find inter-chromosome stop coordinates for requested chroms
            infile.seek( ( skip + num_chroms + chr_index1 ) * int_float32_size, 1 )
            self.header[ 'stop1' ] = struct.unpack( '>i', infile.read( int_float32_size ) )[0]
            infile.seek( ( chr_index2 - chr_index1 - 1 ) * int_float32_size, 1 )
            self.header[ 'stop2' ] = struct.unpack( '>i', infile.read( int_float32_size ) )[0]
            skip = num_chroms - chr_index2 - 1
        else:
            # find intra-chromosome stop coordinate for requested chrom
            infile.seek( ( skip + chr_index1 ) * int_float32_size, 1 )
            self.header[ 'stop' ] = struct.unpack( '>i', infile.read( int_float32_size ) )[0]
            if trans:
                # skip inter-chromosomal stop coordinates
                skip = num_chroms * 2 - chr_index1 - 1
            else:
                skip = num_chroms - chr_index1 - 1

        # get minimum score
        infile.seek( ( skip + pairing_index ) * int_float32_size, 1 )
        self.header[ 'minscore' ] = struct.unpack( '>f', infile.read( int_float32_size ) )[0]
        skip = num_pairings - pairing_index - 1

        # get maximum score
        infile.seek( ( skip + pairing_index ) * int_float32_size, 1 )
        self.header[ 'maxscore' ] = struct.unpack( '>f', infile.read( int_float32_size ) )[0]
        skip = num_pairings - pairing_index - 1

        # get maximum bin size (lowest resolution)
        if chr_index1 != chr_index2:
            # skip intra-chromosomal largest bin size
            skip += 1
        infile.seek( skip * int_float32_size, 1 )
        self.header[ 'lres'] = struct.unpack( '>i', infile.read( int_float32_size ) )[0]

        # get minimum bin size (highest resolution)
        if trans:
            # skip intra- or interchromosomal value (whichever is unneeded)
            infile.seek( int_float32_size, 1 )
        self.header[ 'hres'] = struct.unpack( '>i', infile.read( int_float32_size ) )[0]

        return self.header

    def paint_cis_canvas( self, infile ):
        """
        """
        if ( min( self.stop1, self.stop2 ) <= self.header[ 'start' ] or
             max( self.start1, self.start2 ) >= self.header[ 'stop' ] ):
            return []
        # ensure positions are within bounds of data present in file
        start_pos1 = max( 0, ( self.start1 - self.header[ 'start' ] ) / self.header[ 'lres' ] )
        end_pos1 = min( self.header[ 'n' ], ( self.stop1 - self.header[ 'start' ] - 1 ) / self.header[ 'lres' ] + 1 )
        start_pos2 = max( 0, ( self.start2 - self.header[ 'start' ] ) / self.header[ 'lres' ] )
        end_pos2 = min( self.header[ 'n' ], ( self.stop2 - self.header[ 'start' ] - 1 ) / self.header[ 'lres' ] + 1 )

        if self.overlap:
            # if data overlap, break query into two parts, since data only covers upper-triangle
            outdata = []
            mid_coord = min(self.stop1, self.stop2)
            mid_start = min( self.header[ 'n' ], ( mid_coord - self.header[ 'start' ] ) / self.header[ 'lres' ] )
            mid_stop = min( self.header[ 'n' ], ( mid_coord - self.header[ 'start' ] ) / self.header[ 'lres' ] + 1 )
            if self.start1 <= self.start2:
                self.reverse = False
                self.eff_start1, self.eff_start2 = self.start1, self.start2
                self.eff_stop1, self.eff_stop2 = self.stop1, self.stop2
                outdata += self.paint_cis_upper_level( infile, start_pos1, mid_stop, start_pos2, mid_stop )
            else:
                self.reverse = True
                self.eff_start2, self.eff_start1 = self.start1, self.start2
                self.eff_stop2, self.eff_stop1 = self.stop1, self.stop2
                outdata += self.paint_cis_upper_level( infile, start_pos2, mid_stop, start_pos1, mid_stop )
            if self.stop1 > mid_coord:
                self.reverse = True
                self.eff_start2, self.eff_start1 = self.start1, self.start2
                self.eff_stop2, self.eff_stop1 = self.stop1, self.stop2
                outdata += self.paint_cis_upper_level( infile, start_pos2, end_pos2, mid_start, end_pos1 )
            elif self.stop2 > mid_coord:
                self.reverse = False
                self.eff_start1, self.eff_start2 = self.start1, self.start2
                self.eff_stop1, self.eff_stop2 = self.stop1, self.stop2
                outdata += self.paint_cis_upper_level( infile, start_pos1, end_pos1, mid_start, end_pos2 )

        # if data don't overlap, figure out which range is upstream
        elif self.start2 < self.start1:
            self.reverse = True
            self.eff_start2, self.eff_start1 = self.start1, self.start2
            self.eff_stop2, self.eff_stop1 = self.stop1, self.stop2
            outdata = self.paint_cis_upper_level( infile, start_pos2, end_pos2, start_pos1, end_pos1 )
        else:
            self.reverse = False
            self.eff_start1, self.eff_start2 = self.start1, self.start2
            self.eff_stop1, self.eff_stop2 = self.stop1, self.stop2
            outdata = self.paint_cis_upper_level( infile, start_pos1, end_pos1, start_pos2, end_pos2 )
        return outdata

    def paint_cis_upper_level( self, infile, start_pos1, end_pos1, start_pos2, end_pos2 ):
        """
        """
        outdata = []
        resolution = self.header[ 'lres' ]
        for i in range( start_pos1, end_pos1 ):
            span = end_pos2 - max( start_pos2, i )
            if span == 0:
                continue
            pos_index = i * ( self.header[ 'n' ] - 1 ) - ( i * ( i - 1 ) ) / 2 + max( i, start_pos2 )
            # Find position in file for data with 'i' as upstream interaction
            infile.seek( self.header[ 'offset' ] + pos_index * 4 )
            data = struct.unpack( '>' + 'f' * span, infile.read( span * 4 ) )
            # Find position in file for indices with 'i' as upstream interaction
            infile.seek( self.header[ 'offset' ] + ( pos_index + self.header[ 'data_bins' ] ) * 4 )
            indices = struct.unpack( '>' + 'i' * span, infile.read( span * 4 ) )
            # Find position in file for shapes with 'i' as upstream interaction
            infile.seek( self.header[ 'offset' ] + ( self.header[ 'data_bins' ] +
                         self.header[ 'index_bins' ] ) * 4 + pos_index * 2 )
            shapes = struct.unpack( '>' + 'h' * span,
                      infile.read( span * 2 ) )
            start1 = i * resolution + self.header[ 'start' ]
            for j in range( max( start_pos2, i ), end_pos2 ):
                k = j - max( start_pos2, i )
                # if data is valid, seek down to lower levels for smaller bin sizes
                if not math.isnan( data[k] ):
                    start2 = j * resolution + self.header[ 'start' ]
                    # if valid lower-level data exists, try retrieving it
                    if indices[k] != -1:
                        valid, new_outdata = self.paint_cis_lower_level( infile, indices[k], shapes[k],
                                                               resolution / 2, start1, start2 )
                    else:
                        valid = 0
                    if start1 == start2:
                        # if data is on the diagonal and not completely covered by lower-level data,
                        # only add one square
                        if resolution <= self.minresolution and valid < 3:
                            outdata.append( [start1, start2, resolution, data[k]] )
                    else:
                        # if data is off-diagonal and not completely covered by lower-level data, add it to dataset
                        if resolution <= self.minresolution and valid < 4:
                            outdata.append( [start1, start2, resolution, data[k]] )
                            # if data is off-diagonal, check if the mirror image is also needed
                            if self.overlap and start2 + resolution > self.eff_start1 and start1 < self.eff_stop2:
                                outdata.append( [start2, start1, resolution, data[k]] )
                    if valid > 0:
                        outdata += new_outdata
        # if sequence 2 was upstream of sequence 1, flip the x and y coordinates
        if self.reverse:
            for i in range( len( outdata ) ):
                outdata[i] = [ outdata[i][1], outdata[i][0] ] + outdata[i][2:]
        return outdata

    def paint_cis_lower_level( self, infile, index, shape, resolution, start1, start2 ):
        """
        """
        # don't return data the is higher resolution than requested
        if resolution < self.maxresolution:
            return 0, []
        outdata = []
        valid = 0
        shape = bin(shape)[2:].rjust( 4, '0' )
        num_data = shape.count('1')
        infile.seek( self.header[ 'offset' ] + index * 4 )
        data = struct.unpack( '>' + 'f' * num_data, infile.read( 4 * num_data ) )
        if index < self.header[ 'index_bins' ]:
            infile.seek( self.header[ 'offset' ] + ( index + self.header[ 'data_bins' ] ) * 4 )
            indices = struct.unpack( '>' + 'i' * num_data, infile.read( num_data * 4 ) )
            infile.seek( self.header[ 'offset' ] + ( self.header[ 'data_bins' ] + self.header[ 'index_bins' ] ) * 4 +
                         index * 2 )
            shapes = struct.unpack( '>' + 'h' * num_data, infile.read( num_data * 2 ) )
        else:
            indices = None
            shapes = None
        # for each bin, find if it has valid data, and if lower levels need to be queried
        pos = 0
        for i in range( 2 ):
            for j in range( 2 ):
                if shape[ -1 - j - i * 2 ] == '0':
                    continue
                if not math.isnan( data[pos] ):
                    start1b = start1 + i * resolution
                    start2b = start2 + j * resolution
                    # if the bin is valid but out of the query range, do return data
                    if ( start1b > self.eff_stop1 or start1b + resolution < self.eff_start1 or
                         start2b > self.eff_stop2 or start2b + resolution < self.eff_start2 ):
                        valid += 1
                    else:
                        # if the bin is valid and has valid data at a lower level, go down a level
                        if indices is not None and indices[pos] != -1:
                            new_valid, new_outdata = self.paint_cis_lower_level( infile, indices[pos], shapes[pos],
                                                     resolution / 2, start1b, start2b )
                        else:
                            new_valid = 0
                        # if data is high enough resolution and isn't completely covered by
                        # lower-level bins, return bin data
                        if resolution <= self.minresolution:
                            if start1b == start2b:
                                if new_valid < 3:
                                    outdata.append( [start1b, start2b, resolution, data[pos]] )
                            else:
                                if new_valid < 4:
                                    outdata.append( [start1b, start2b, resolution, data[pos]] )
                                if ( self.overlap and start2b + resolution > self.eff_start1 and
                                     start1b < self.eff_stop2 ):
                                    outdata.append( [start2b, start1b, resolution, data[pos]] )
                        if new_valid > 0:
                            outdata += new_outdata
                        valid += 1
                pos += 1
        return valid, outdata

    def paint_trans_canvas( self, infile ):
        """
        """
        outdata = []
        start_pos1 = max( 0, ( self.start1 - self.header[ 'start1' ] ) / self.header[ 'lres' ] )
        end_pos1 = min( self.header[ 'n' ], ( self.stop1 - self.header[ 'start1' ] - 1 ) / self.header[ 'lres' ] + 1 )
        start_pos2 = max( 0, ( self.start2 - self.header[ 'start2' ] ) / self.header[ 'lres' ] )
        end_pos2 = min( self.header[ 'm' ], ( self.stop2 - self.header[ 'start2' ] - 1 ) / self.header[ 'lres' ] + 1 )
        resolution = self.header[ 'lres' ]
        if end_pos2 <= start_pos2:
            return outdata

        for i in range( start_pos1, end_pos1 ):
            pos_index = i * self.header[ 'm' ] + start_pos2
            # Find position in file for data with 'i' as upstream interaction
            infile.seek( self.header[ 'offset' ] + pos_index * 4 )
            data = struct.unpack( '>' + 'f' * ( end_pos2 - start_pos2 ), infile.read( ( end_pos2 - start_pos2 ) * 4 ) )
            # Find position in file for indices with 'i' as upstream interaction
            infile.seek( self.header[ 'offset' ] + ( pos_index + self.header[ 'data_bins' ] ) * 4 )
            indices = struct.unpack( '>' + 'i' * ( end_pos2 - start_pos2 ),
                infile.read( ( end_pos2 - start_pos2 ) * 4 ) )
            # Find position in file for shapes with 'i' as upstream interaction
            infile.seek( self.header[ 'offset' ] + ( self.header[ 'data_bins' ] + self.header[ 'index_bins' ] ) * 4 +
                         pos_index * 2 )
            shapes = struct.unpack( '>' + 'h' * ( end_pos2 - start_pos2 ),
                infile.read( ( end_pos2 - start_pos2 ) * 2 ) )
            for j in range( start_pos2, end_pos2 ):
                k = j - start_pos2
                # if data is valid, seek down to lower levels for smaller bin sizes
                if not math.isnan( data[k] ):
                    start1 = i * resolution + self.header[ 'start1' ]
                    start2 = j * resolution + self.header[ 'start2' ]
                    # if valid lower-level data exists, try retrieving it
                    if indices[k] != -1:
                        new_valid, new_outdata = self.paint_trans_lower_level( infile, indices[k], shapes[k],
                                                 resolution / 2, start1, start2 )
                    else:
                        new_valid = 0
                    # if top-level square not completely covered by lower-level squares, add it to dataset
                    if resolution <= self.minresolution and new_valid < 4:
                        outdata.append( [start1, start2, resolution, data[k]] )
                    if new_valid > 0:
                        outdata += new_outdata
        return outdata

    def paint_trans_lower_level( self, infile, index, shape, resolution, start1, start2 ):
        """
        """
        # don't return data the is higher resolution than requested
        if resolution < self.maxresolution:
            return 0, []
        outdata = []
        valid = 0
        shape = bin(shape)[2:].rjust( 4, '0' )
        num_data = shape.count('1')
        infile.seek( self.header[ 'offset' ] + index * 4 )
        data = struct.unpack( '>' + 'f' * num_data, infile.read( 4 * num_data ) )
        if index < self.header[ 'index_bins' ]:
            infile.seek( self.header[ 'offset' ] + ( index + self.header[ 'data_bins' ] ) * 4 )
            indices = struct.unpack( '>' + 'i' * num_data, infile.read( num_data * 4 ) )
            infile.seek( self.header[ 'offset' ] + ( self.header[ 'data_bins' ] + self.header[ 'index_bins' ] ) * 4 +
                         index * 2 )
            shapes = struct.unpack( '>' + 'h' * num_data, infile.read( num_data * 2 ) )
        else:
            indices = None
            shapes = None
        # for each bin, find if it has valid data, and if lower levels need to be queried
        pos = 0
        for i in range( 2 ):
            for j in range( 2 ):
                if shape[ -1 - ( i * 2 + j ) ] == '0':
                    continue
                if not math.isnan( data[pos] ):
                    start1b = start1 + i * resolution
                    start2b = start2 + j * resolution
                    # if the bin is valid but out of the query range, do return data
                    if ( start1b > self.stop1 or start1b + resolution < self.start1 or
                         start2b > self.stop2 or start2b + resolution < self.start2 ):
                        valid += 1
                    else:
                        if indices is not None and indices[pos] != -1:
                            new_valid, new_outdata = self.paint_trans_lower_level( infile, indices[pos], shapes[pos],
                                                     resolution / 2, start1b, start2b )
                        else:
                            new_valid = 0
                        # if data is high enough resolution and isn't completely covered by
                        # lower-level bins, return bin data
                        if resolution <= self.minresolution and new_valid < 4:
                            outdata.append( [start1b, start2b, resolution, data[pos]] )
                        if new_valid > 0:
                            outdata += new_outdata
                        valid += 1
                pos += 1
        return valid, outdata

    def interpolate_square( self, square ):
        """
        """
        if self.start1 >= self.stop1 or self.start2 >= self.stop2:
            return
        x1 = max( square[0], self.start1 )
        xspan = min( square[0] + square[2] - x1, self.stop1 - x1 )
        y1 = max( square[1], self.start2 )
        yspan = min( square[1] + square[2] - y1, self.stop2 - y1 )
        r = self.levels[ square[2] ]
        if self.transpose:
            square_list = [ y1, yspan, x1, xspan, square[3], r ]
        else:
            square_list = [ x1, xspan, y1, yspan, square[3], r ]
        return square_list
