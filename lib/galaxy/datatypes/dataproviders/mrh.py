"""
"""
import binascii
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
        'start1'        : 'long',
        'start2'        : 'long',
        'window_size'   : 'long',
        'resolution'    : 'long',
        'header'        : 'bool',
    }

    def __init__( self, source, start1=0, start2=0, window_size=0, resolution=0, header=False, **kwargs ):
        """
        :param start1: starting bp in sequence 1
        :type start1: long

        :param start2: starting bp in sequence 2
        :type start2: long

        :param window_size: number of bp to compare
        :type window_size: long

        :param resolution: ???
        :type resolution: long

        :param header: T/F send header data instead
        :type resolution: bool
        """
        super( MrhSquareDataProvider, self ).__init__( source, **kwargs )
        self.start1 = start1
        self.start2 = start2
        self.width = window_size
        self.maxres = resolution
        self.header_only = header

        self.transpose = False
        if start1 > start2:
            self.transpose = True
            self.start1, self.start2 = self.start2, self.start1
        self.stop1 = self.start1 + self.width
        self.stop2 = self.start2 + self.width
        self.overlap = self.stop1 > self.start2
        # print self.start1, self.stop1
        # print self.start2, self.stop2
        # print self.width, self.maxres
        # print self.overlap
        # print self.transpose
        # print self.header_only

    def __iter__( self ):
        with self.source as infile:
            self.load_header( infile )
            if self.header_only:
                yield self.header
            else:
                for square in self.paint_canvas( infile ):
                    square = self.interpolate_square( square )
                    yield square

    def load_header( self, infile ):
        """
        """
        # get and validate magic number for mrh type
        mrh_magic_number = '42054205'
        mrh_magic_number_size = 4
        magic_number = binascii.b2a_hex( infile.read( mrh_magic_number_size ) )
        if magic_number != mrh_magic_number:
            raise TypeError( 'File does not appear to be a multi-resolution heatmap file' )

        # get the recorded header/meta fields
        header_field_names = [ 'lres', 'hres', 'zoom', 'minobs', 'start', 'n_bins', 'd_bins', 't_bins' ]
        num_header_fields = len( header_field_names )
        int32_size = 4
        header_fields = struct.unpack( 'i' * num_header_fields, infile.read( int32_size * num_header_fields ) )
        self.header = dict( zip( header_field_names, header_fields ) )

        # get the fields derived from the recorded fields
        lres, hres, zoom, minobs, start, n_bins, d_bins, t_bins = header_fields
        end_of_header_offset = ( int32_size * num_header_fields ) + mrh_magic_number_size
        self.header[ 'offset' ] = end_of_header_offset
        n_levels = math.log( lres / float( hres ) ) / math.log( zoom )
        n_levels = int( round( n_levels ) ) + 1
        self.header[ 'n_levels' ] = n_levels
        self.header[ 'n' ] = int( ( 0.25 + 2 * n_bins ) ** 0.5 - 0.5 )
        self.header[ 'i_bins' ] = t_bins - d_bins
        self.header[ 'zoom2' ] = zoom ** 2

        # print self.header
        return self.header

    def paint_canvas( self, infile ):
        """
        """
        outdata = []
        start_pos1 = max( 0, ( self.start1 - self.header['start'] ) / self.header['lres'] )
        end_pos1 = min( self.header['n'], ( self.stop1 - self.header['start'] ) / self.header['lres'] + 1 )
        start_pos2 = max( 0, ( self.start2 - self.header['start'] ) / self.header['lres'] )
        end_pos2 = min( self.header['n'], ( self.stop2 - self.header['start'] ) / self.header['lres'] + 1 )
        resolution = self.header['lres']

        for i in range( start_pos1, end_pos1 ):
            # Find position in file for data with 'i' as upstream interaction
            infile.seek( self.header['offset'] + ( i * ( self.header['n'] - 1 ) - ( i * ( i - 1 ) ) / 2 + max( i, start_pos2 ) ) * 4 )
            data = struct.unpack( 'f' * ( end_pos2 - max( start_pos2, i ) ), infile.read( ( end_pos2 - max( start_pos2, i ) ) * 4 ) )
            # Find position in file for indices with 'i' as upstream interaction
            infile.seek( self.header['offset'] + ( i * ( self.header['n'] - 1 ) - ( i * ( i - 1 ) ) / 2 + self.header['d_bins'] +
                        max( i, start_pos2 ) ) * 4 )
            indices = struct.unpack( 'i' * ( end_pos2 - max( start_pos2, i ) ),
                                    infile.read( ( end_pos2 - max( start_pos2, i ) ) * 4 ) )
            for j in range( max( start_pos2, i ), end_pos2 ):
                k = j - max( start_pos2, i )
                if not math.isnan( data[k] ):
                    start1 = i * resolution + self.header['start']
                    start2 = j * resolution + self.header['start']
                    if indices[k] != -1:
                        valid, new_outdata = self.paint_lower_level( infile, indices[k],
                                                               resolution / self.header['zoom'], start1, start2 )
                        if valid < self.header['zoom2']:
                            outdata.append( [start1, start2, resolution, data[k]] )
                            if ( self.overlap and start1 != start2 and start2 + resolution > self.start1 and
                                 start1 < self.stop2 ):
                                outdata.append( [start2, start1, resolution, data[k]] )
                        outdata += new_outdata
                    else:
                        outdata.append( [start1, start2, resolution, data[k]] )
        return outdata

    def paint_lower_level( self, infile, index, resolution, start1, start2 ):
        """
        """
        if resolution < self.maxres:
            return 0, []
        outdata = []
        valid = 0
        infile.seek( self.header['offset'] + index * 4 )
        if start1 == start2:
            data = struct.unpack( 'f' * ( self.header['zoom'] * ( self.header['zoom'] + 1 ) / 2 ),
                                 infile.read( 2 * self.header['zoom'] * ( self.header['zoom'] + 1 ) ) )
            if index < self.header['i_bins']:
                infile.seek( self.header['offset'] + ( index + self.header['d_bins'] ) * 4 )
                indices = struct.unpack( 'i' * ( self.header['zoom'] * ( self.header['zoom'] + 1 ) / 2 ),
                                        infile.read( self.header['zoom'] * ( self.header['zoom'] + 1 ) * 2 ) )
            else:
                indices = None
            for i in range( self.header['zoom'] ):
                for j in range( i, self.header['zoom'] ):
                    k = i * ( self.header['zoom'] - 1 ) - ( i * ( i - 1 ) ) / 2 + j
                    if not math.isnan( data[k] ):
                        start1b = start1 + i * resolution
                        start2b = start2 + j * resolution
                        if ( start1b > self.stop1 or start1b + resolution < self.start1 or
                             start2b > self.stop2 or start2b + resolution < self.start2 ):
                            valid += 1
                        else:
                            if indices is not None and indices[k] != -1:
                                new_valid, new_outdata = self.paint_lower_level( infile, indices[k],
                                                         resolution / self.header['zoom'], start1b, start2b )
                                if start1b == start2b:
                                    if new_valid < self.header['zoom'] * ( self.header['zoom'] + 1 ) / 2:
                                        outdata.append( [start1b, start2b, resolution, data[k]] )
                                else:
                                    if new_valid < self.header['zoom2']:
                                        outdata.append( [start1b, start2b, resolution, data[k]] )
                                        if ( self.overlap and start2b + resolution > self.start1 and
                                             start1b < self.stop2 ):
                                            outdata.append( [start2b, start1b, resolution, data[k]] )
                                outdata += new_outdata
                                valid += 1
        else:
            data = struct.unpack( 'f' * self.header['zoom2'], infile.read( 4 * self.header['zoom2'] ) )
            if index < self.header['i_bins']:
                infile.seek( self.header['offset'] + ( index + self.header['d_bins'] ) * 4 )
                indices = struct.unpack( 'i' * self.header['zoom2'], infile.read( self.header['zoom2'] * 4 ) )
            else:
                indices = None
            for i in range( self.header['zoom2'] ):
                if not math.isnan( data[i] ):
                    start1b = start1 + ( i / self.header['zoom'] ) * resolution
                    start2b = start2 + ( i % self.header['zoom'] ) * resolution
                    if ( start1b > self.stop1 or start1b + resolution < self.start1 or
                         start2b > self.stop2 or start2b + resolution < self.start2 ):
                        valid += 1
                    else:
                        if indices is not None and indices[i] != -1:
                            new_valid, new_outdata = self.paint_lower_level( infile, indices[i],
                                                     resolution / self.header['zoom'], start1b, start2b )
                            if new_valid < self.header['zoom2']:
                                outdata.append( [start1b, start2b, resolution, data[i]] )
                                if self.overlap and start2b + resolution > self.start1 and start1b < self.stop2:
                                    outdata.append( [start2b, start1b, resolution, data[i]] )
                            outdata += new_outdata
                            valid += 1
        return valid, outdata

    def interpolate_square( self, square ):
        """
        """
        width = float( self.width )
        if width == 0:
            return

        x = square[0] - self.start1
        y = square[1] - self.start2
        square_dict = {
            'x1' : min( max( x / width, 0.0 ), 1.0 ),
            'y1' : min( max( y / width, 0.0 ), 1.0 ),
            'x2' : min( max( ( x + square[2] ) / width, 0.0 ), 1.0 ),
            'y2' : min( max( ( y + square[2] ) / width, 0.0 ), 1.0 ),
            'value' : square[3]
        }
        if self.transpose:
            square_dict.update({
                'x1' : square_dict['y1'], 'y1' : square_dict['x1'],
                'x2' : square_dict['y2'], 'y2' : square_dict['x2'], 'value' : square[3]
            })
        return square_dict
