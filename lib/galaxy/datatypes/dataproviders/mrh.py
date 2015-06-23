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
        'start1'         : 'long',
        'stop1'          : 'long',
        'start2'         : 'long',
        'stop2'          : 'long',
        'min_resolution' : 'long',
        'max_resolution' : 'long',
        'header'         : 'bool',
        'trans'          : 'bool',
        'transpose'      : 'bool',
    }

    def __init__( self, source, start1=0, stop1=0, start2=0, stop2=0, min_resolution=0, max_resolution=5120000,
                  header=False, trans=False, transpose=False, **kwargs ):
        """
        :param start1: starting bp in sequence 1
        :type start1: long

        :param stop1: stopping bp in sequence 1
        :type stop1: long

        :param start2: starting bp in sequence 2
        :type start2: long

        :param stop2: stopping bp in sequence 2
        :type stop2: long

        :param min_resolution: largest bin size to return
        :type min_resolution: long

        :param max_resolution: smallest bin size to return
        :type max_resolution: long

        :param header: T/F send header data instead
        :type resolution: bool

        :param trans: T/F data requested is inter-chromosomal
        :type trans: bool

        :param transpose: T/F flip X/Y axes (trans data only)
        :type transpose: bool
        """
        super( MrhSquareDataProvider, self ).__init__( source, **kwargs )
        self.start1 = start1
        self.start2 = start2
        self.stop1 = stop1
        self.stop2 = stop2
        self.minres = min_resolution
        self.maxres = max_resolution
        self.header_only = header
        self.trans = trans
        self.transpose = transpose

        if not trans and (stop1 > start2 or stop2 > start1):
            self.overlap = True
        else:
            self.overlap = False
        self.window1 = self.stop1 - self.start1
        self.window2 = self.stop2 - self.start2
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
                if self.trans:
                    for square in self.paint_trans_canvas( infile ):
                        square = self.interpolate_square( square )
                        yield square
                else:
                    for square in self.paint_cis_canvas( infile ):
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

        # get the first half of recorded header/meta fields
        header_field_names = [ 'offset', 'lres', 'hres', 'zoom', 'minobs', 'minscore', 'maxscore', 'trans']
        header_field_types = 'iiiiiffi'
        num_header_fields = len( header_field_names )
        int32_size = 4
        header_fields = struct.unpack( header_field_types, infile.read( int32_size * num_header_fields ) )
        # determine if mrh file contains trans data
        if header_fields[-1]:
            # get the remaining header/meta fields
            header2_field_names = ['start', 'start2', 'stop', 'stop2', 'n', 'm', 'd_bins', 't_bins', 'n_bins']
            num_header2_fields = len( header2_field_names )
            header_fields += struct.unpack( 'i' * num_header2_fields, infile.read( int32_size * num_header2_fields ) )
            header_field_names += header2_field_names
        else:
            # get the remaining header/meta fields
            header2_field_names = ['start', 'stop', 'n', 'd_bins', 't_bins', 'n_bins']
            num_header2_fields = len( header2_field_names )
            header_fields += struct.unpack( 'i' * num_header2_fields, infile.read( int32_size * num_header2_fields ) )
            header_field_names += header2_field_names
        self.header = dict( zip( header_field_names, header_fields ) )

        # get the fields derived from the recorded fields
        lres, hres, zoom = self.header['lres'], self.header['hres'], self.header['zoom']
        n_levels = math.log( lres / float( hres ) ) / math.log( zoom )
        n_levels = int( round( n_levels ) ) + 1
        self.header[ 'n_levels' ] = n_levels
        self.header[ 'zoom2' ] = zoom ** 2
        self.header['zoom_d'] = (zoom * (zoom + 1)) / 2
        d_bins, t_bins = self.header['d_bins'], self.header['t_bins']
        self.header[ 'i_bins' ] = t_bins - d_bins

        # print self.header
        return self.header

    def paint_cis_canvas( self, infile ):
        """
        """
        if ( min( self.stop1, self.stop2 ) <= self.header['start'] or
             max( self.start1, self.start2 ) >= self.header['stop'] ):
            return []
        start_pos1 = max( 0, ( self.start1 - self.header['start'] ) / self.header['lres'] )
        end_pos1 = min( self.header['n'], ( self.stop1 - self.header['start'] ) / self.header['lres'] + 1 )
        start_pos2 = max( 0, ( self.start2 - self.header['start'] ) / self.header['lres'] )
        end_pos2 = min( self.header['n'], ( self.stop2 - self.header['start'] ) / self.header['lres'] + 1 )
        if self.overlap:
            outdata = []
            mid_coord = min(self.stop1, self.stop2)
            mid_start = min( self.header['n'], ( mid_coord - self.header['start'] ) / self.header['lres'] )
            mid_stop = min( self.header['n'], ( mid_coord - self.header['start'] ) / self.header['lres'] ) + 1
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
                self.revese = True
                self.eff_start2, self.eff_start1 = self.start1, self.start2
                self.eff_stop2, self.eff_stop1 = self.stop1, self.stop2
                outdata += self.paint_cis_upper_level( infile, start_pos2, end_pos2, mid_start, end_pos1 )
            elif self.stop2 > mid_coord:
                self.reverse = False
                self.eff_start1, self.eff_start2 = self.start1, self.start2
                self.eff_stop1, self.eff_stop2 = self.stop1, self.stop2
                outdata += self.paint_cis_upper_level( infile, start_pos1, end_pos1, mid_start, end_pos2 )
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
                        valid, new_outdata = self.paint_cis_lower_level( infile, indices[k],
                                                               resolution / self.header['zoom'], start1, start2 )
                    else:
                        valid = 0
                    if start1 == start2:
                        if resolution <= self.minres and valid < self.header['zoom_d']:
                            outdata.append( [start1, start2, resolution, data[k]] )
                    else:
                        if resolution <= self.minres and valid < self.header['zoom2']:
                            outdata.append( [start1, start2, resolution, data[k]] )
                            if self.overlap and start2 + resolution > self.eff_start1 and start1 < self.eff_stop2:
                                outdata.append( [start2, start1, resolution, data[k]] )
                    if valid > 0:
                        outdata += new_outdata
        if self.reverse:
            for i in range( len( outdata ) ):
                outdata[i] = [ outdata[i][1], outdata[i][0] ] + outdata[i][2:]
        return outdata

    def paint_cis_lower_level( self, infile, index, resolution, start1, start2 ):
        """
        """
        if resolution < self.maxres:
            return 0, []
        outdata = []
        valid = 0
        infile.seek( self.header['offset'] + index * 4 )
        if start1 == start2:
            data = struct.unpack( 'f' * self.header['zoom_d'], infile.read( 4 * self.header['zoom_d'] ) )
            if index < self.header['i_bins']:
                infile.seek( self.header['offset'] + ( index + self.header['d_bins'] ) * 4 )
                indices = struct.unpack( 'i' * self.header['zoom_d'], infile.read( self.header['zoom_d'] * 4 ) )
            else:
                indices = None
            for i in range( self.header['zoom'] ):
                for j in range( i, self.header['zoom'] ):
                    k = i * ( self.header['zoom'] - 1 ) - ( i * ( i - 1 ) ) / 2 + j
                    if not math.isnan( data[k] ):
                        start1b = start1 + i * resolution
                        start2b = start2 + j * resolution
                        if ( start1b >= self.eff_stop1 or start1b + resolution <= self.eff_start1 or
                             start2b >= self.eff_stop2 or start2b + resolution <= self.eff_start2 ):
                            valid += 1
                        else:
                            if indices is not None and indices[k] != -1:
                                new_valid, new_outdata = self.paint_cis_lower_level( infile, indices[k],
                                                         resolution / self.header['zoom'], start1b, start2b )
                            else:
                                new_valid = 0
                            if resolution  <= self.minres:
                                if start1b == start2b:
                                    if new_valid < self.header['zoom_d']:
                                        outdata.append( [start1b, start2b, resolution, data[k]] )
                                else:
                                    if new_valid < self.header['zoom2']:
                                        outdata.append( [start1b, start2b, resolution, data[k]] )
                                        if ( self.overlap and start2b + resolution > self.eff_start1 and
                                             start1b < self.eff_stop2 ):
                                            outdata.append( [start2b, start1b, resolution, data[k]] )
                            if new_valid > 0:
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
                    if ( start1b > self.eff_stop1 or start1b + resolution < self.eff_start1 or
                         start2b > self.eff_stop2 or start2b + resolution < self.eff_start2 ):
                        valid += 1
                    else:
                        if indices is not None and indices[i] != -1:
                            new_valid, new_outdata = self.paint_cis_lower_level( infile, indices[i],
                                                     resolution / self.header['zoom'], start1b, start2b )
                        else:
                            new_valid = 0
                        if resolution <= self.minres and new_valid < self.header['zoom2']:
                            outdata.append( [start1b, start2b, resolution, data[i]] )
                            if self.overlap and start2b + resolution > self.eff_start1 and start1b < self.eff_stop2:
                                outdata.append( [start2b, start1b, resolution, data[i]] )
                        if new_valid > 0:
                            outdata += new_outdata
                        valid += 1
        return valid, outdata

    def paint_trans_canvas( self, infile ):
        """
        """
        outdata = []
        start_pos1 = max( 0, ( self.start1 - self.header['start'] ) / self.header['lres'] )
        end_pos1 = min( self.header['n'], ( self.stop1 - self.header['start'] ) / self.header['lres'] + 1 )
        start_pos2 = max( 0, ( self.start2 - self.header['start2'] ) / self.header['lres'] )
        end_pos2 = min( self.header['m'], ( self.stop2 - self.header['start2'] ) / self.header['lres'] + 1 )
        resolution = self.header['lres']

        for i in range( start_pos1, end_pos1 ):
            # Find position in file for data with 'i' as upstream interaction
            infile.seek( self.header['offset'] + i * self.header['m'] * 4 )
            data = struct.unpack( 'f' * ( end_pos2 - start_pos2 ), infile.read( ( end_pos2 - start_pos2 ) * 4 ) )
            # Find position in file for indices with 'i' as upstream interaction
            infile.seek( self.header['offset'] + ( i * self.header['m'] + self.header['d_bins'] + start_pos2 ) * 4 )
            indices = struct.unpack( 'i' * ( end_pos2 - start_pos2 ), infile.read( ( end_pos2 - start_pos2 ) * 4 ) )
            for j in range( start_pos2, end_pos2 ):
                k = j - start_pos2
                if not math.isnan( data[k] ):
                    start1 = i * resolution + self.header['start']
                    start2 = j * resolution + self.header['start2']
                    if indices[k] != -1:
                        new_valid, new_outdata = self.paint_trans_lower_level( infile, indices[k],
                                                               resolution / self.header['zoom'], start1, start2 )
                    else:
                        new_valid = 0
                    if resolution <= self.minres and valid < self.header['zoom2']:
                        outdata.append( [start1, start2, resolution, data[k]] )
                    if new_valid > 0:
                        outdata += new_outdata
        return outdata

    def paint_trans_lower_level( self, infile, index, resolution, start1, start2 ):
        """
        """
        if resolution < self.maxres:
            return 0, []
        outdata = []
        valid = 0
        infile.seek( self.header['offset'] + index * 4 )
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
                        new_valid, new_outdata = self.paint_trans_lower_level( infile, indices[i],
                                                 resolution / self.header['zoom'], start1b, start2b )
                    else:
                        new_valid = 0
                    if resolution <= self.minres and new_valid < self.header['zoom2']:
                        outdata.append( [start1b, start2b, resolution, data[i]] )
                    if valid > 0:
                        outdata += new_outdata
                    valid += 1
        return valid, outdata

    def interpolate_square( self, square ):
        """
        """
        if self.start1 == self.stop1 or self.start2 == self.stop2:
            return

        square_dict = {
            'x1' : min( max( square[0], self.start1 ), self.stop1 ),
            'y1' : min( max( square[1], self.start2 ), self.stop2 ),
            'x2' : min( max( square[0] + square[2], self.start1 ), self.stop1 ),
            'y2' : min( max( square[1] + square[2], self.start2 ), self.stop2 ),
            'value' : square[3]
        }
        if self.transpose:
            square_dict.update({
                'x1' : square_dict['y1'], 'y1' : square_dict['x1'],
                'x2' : square_dict['y2'], 'y2' : square_dict['x2'], 'value' : square[3]
            })
        return square_dict
