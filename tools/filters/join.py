#!/usr/bin/env python
# Dan Blankenberg
"""
Script to Join Two Files on specified columns.

Takes two tab delimited files, two column numbers (base 1) and outputs a new tab delimited file with lines joined by tabs.
User can also opt to have have non-joining rows of file1 echoed.
"""
from __future__ import print_function

import json
import optparse
import os
import struct
import sys
import tempfile

from galaxy.util import stringify_dictionary_keys
from galaxy.util.bunch import Bunch


class OffsetList:
    def __init__( self, filesize=0, fmt=None ):
        self.file = tempfile.NamedTemporaryFile( 'w+b' )
        if fmt:
            self.fmt = fmt
        elif filesize and filesize <= sys.maxsize * 2:
            self.fmt = 'I'
        else:
            self.fmt = 'Q'
        self.fmt_size = struct.calcsize( self.fmt )

    @property
    def size( self ):
        self.file.flush()
        return self.file_size / self.fmt_size

    @property
    def file_size( self ):
        self.file.flush()
        return os.stat( self.file.name ).st_size

    def add_offset( self, offset ):
        if not isinstance( offset, list ):
            offset = [offset]
        self.file.seek( self.file_size )
        for off in offset:
            self.file.write( struct.pack( self.fmt, off ) )

    def get_offsets( self, start=0 ):
        self.file.seek( start * self.fmt_size )
        while True:
            packed = self.file.read( self.fmt_size )
            if not packed:
                break
            yield struct.unpack( self.fmt, packed )[0]

    def get_offset_by_index( self, index ):
        self.file.seek( index * self.fmt_size )
        return struct.unpack( self.fmt, self.file.read( self.fmt_size ) )[0]

    def set_offset_at_index( self, index, offset ):
        if not isinstance( offset, list ):
            offset = [offset]
        if index >= self.size:
            self.add_offset( offset )
        else:
            temp_file = tempfile.NamedTemporaryFile( 'w+b' )
            self.file.seek( 0 )
            temp_file.write( self.file.read( ( index ) * self.fmt_size ) )
            for off in offset:
                temp_file.write( struct.pack( self.fmt, off ) )
            temp_file.write( self.file.read() )
            self.file = temp_file


class SortedOffsets( OffsetList ):
    def __init__( self, indexed_filename, column, split=None ):
        OffsetList.__init__( self, os.stat( indexed_filename ).st_size )
        self.indexed_filename = indexed_filename
        self.indexed_file = open( indexed_filename, 'rb' )
        self.column = column
        self.split = split
        self.last_identifier = None
        self.last_identifier_merged = None
        self.last_offset_merged = 0

    def merge_with_dict( self, new_offset_dict ):
        if not new_offset_dict:
            return  # no items to merge in
        keys = list(new_offset_dict.keys())
        keys.sort()
        identifier2 = keys.pop( 0 )

        result_offsets = OffsetList( fmt=self.fmt )
        offsets1 = enumerate( self.get_offsets() )
        try:
            index1, offset1 = next(offsets1)
            identifier1 = self.get_identifier_by_offset( offset1 )
        except StopIteration:
            offset1 = None
            identifier1 = None
            index1 = 0

        while True:
            if identifier1 is None and identifier2 is None:
                self.file = result_offsets.file  # self is now merged results
                return
            elif identifier1 is None or ( identifier2 and identifier2 < identifier1 ):
                result_offsets.add_offset( new_offset_dict[identifier2] )
                if keys:
                    identifier2 = keys.pop( 0 )
                else:
                    identifier2 = None
            elif identifier2 is None:
                result_offsets.file.seek( result_offsets.file_size )
                self.file.seek( index1 * self.fmt_size )
                result_offsets.file.write( self.file.read() )
                identifier1 = None
                offset1 = None
            else:
                result_offsets.add_offset( offset1 )
                try:
                    index1, offset1 = next(offsets1)
                    identifier1 = self.get_identifier_by_offset( offset1 )
                except StopIteration:
                    offset1 = None
                    identifier1 = None
                    index1 += 1

# methods to help link offsets to lines, ids, etc
    def get_identifier_by_line( self, line ):
        if isinstance( line, str ):
            fields = line.rstrip( '\r\n' ).split( self.split )
            if self.column < len( fields ):
                return fields[self.column]
        return None

    def get_line_by_offset( self, offset ):
        self.indexed_file.seek( offset )
        return self.indexed_file.readline()

    def get_identifier_by_offset( self, offset ):
        return self.get_identifier_by_line( self.get_line_by_offset( offset ) )


# indexed set of offsets, index is built on demand
class OffsetIndex:
    def __init__( self, filename, column, split=None, index_depth=3 ):
        self.filename = filename
        self.file = open( filename, 'rb' )
        self.column = column
        self.split = split
        self._offsets = {}
        self._index = None
        self.index_depth = index_depth

    def _build_index( self ):
        self._index = {}
        for start_char, sorted_offsets in self._offsets.items():
            self._index[start_char] = {}
            for i, offset in enumerate( sorted_offsets.get_offsets() ):
                identifier = sorted_offsets.get_identifier_by_offset( offset )
                if identifier[0:self.index_depth] not in self._index[start_char]:
                    self._index[start_char][identifier[0:self.index_depth]] = i

    def get_lines_by_identifier( self, identifier ):
        if not identifier:
            return
        # if index doesn't exist, build it
        if self._index is None:
            self._build_index()

        # identifier cannot exist
        if identifier[0] not in self._index or identifier[0:self.index_depth] not in self._index[identifier[0]]:
            return
        # identifier might exist, search for it
        offset_index = self._index[identifier[0]][identifier[0:self.index_depth]]
        while True:
            if offset_index >= self._offsets[identifier[0]].size:
                return
            offset = self._offsets[identifier[0]].get_offset_by_index( offset_index )
            identifier2 = self._offsets[identifier[0]].get_identifier_by_offset( offset )
            if not identifier2 or identifier2 > identifier:
                return
            if identifier2 == identifier:
                yield self._offsets[identifier[0]].get_line_by_offset( offset )
            offset_index += 1

    def get_offsets( self ):
        keys = list(self._offsets.keys())
        keys.sort()
        for key in keys:
            for offset in self._offsets[key].get_offsets():
                yield offset

    def get_line_by_offset( self, offset ):
        self.file.seek( offset )
        return self.file.readline()

    def get_identifiers_offsets( self ):
        keys = list(self._offsets.keys())
        keys.sort()
        for key in keys:
            for offset in self._offsets[key].get_offsets():
                yield self._offsets[key].get_identifier_by_offset( offset ), offset

    def get_identifier_by_line( self, line ):
        if isinstance( line, str ):
            fields = line.rstrip( '\r\n' ).split( self.split )
            if self.column < len( fields ):
                return fields[self.column]
        return None

    def merge_with_dict( self, d ):
        if not d:
            return  # no data to merge
        self._index = None
        keys = list(d.keys())
        keys.sort()
        identifier = keys.pop( 0 )
        first_char = identifier[0]
        temp = { identifier: d[identifier] }
        while True:
            if not keys:
                if first_char not in self._offsets:
                    self._offsets[first_char] = SortedOffsets( self.filename, self.column, self.split )
                self._offsets[first_char].merge_with_dict( temp )
                return
            identifier = keys.pop( 0 )
            if identifier[0] == first_char:
                temp[identifier] = d[identifier]
            else:
                if first_char not in self._offsets:
                    self._offsets[first_char] = SortedOffsets( self.filename, self.column, self.split )
                self._offsets[first_char].merge_with_dict( temp )
                temp = { identifier: d[identifier] }
                first_char = identifier[0]


class BufferedIndex:
    def __init__( self, filename, column, split=None, buffer=1000000, index_depth=3 ):
        self.index = OffsetIndex( filename, column, split, index_depth )
        self.buffered_offsets = {}
        f = open( filename, 'rb' )
        offset = f.tell()
        identified_offset_count = 1
        while True:
            offset = f.tell()
            line = f.readline()
            if not line:
                break  # EOF
            identifier = self.index.get_identifier_by_line( line )
            if identifier:
                # flush buffered offsets, if buffer size reached
                if buffer and identified_offset_count % buffer == 0:
                    self.index.merge_with_dict( self.buffered_offsets )
                    self.buffered_offsets = {}
                if identifier not in self.buffered_offsets:
                    self.buffered_offsets[identifier] = []
                self.buffered_offsets[identifier].append( offset )
                identified_offset_count += 1
        f.close()

    def get_lines_by_identifier( self, identifier ):
        for line in self.index.get_lines_by_identifier( identifier ):
            yield line
        if identifier in self.buffered_offsets:
            for offset in self.buffered_offsets[identifier]:
                yield self.index.get_line_by_offset( offset )


def fill_empty_columns( line, split, fill_values ):
    if not fill_values:
        return line
    filled_columns = []
    for i, field in enumerate( line.split( split ) ):
        if field or i >= len( fill_values ):
            filled_columns.append( field )
        else:
            filled_columns.append( fill_values[i] )
    if len( fill_values ) > len( filled_columns ):
        filled_columns.extend( fill_values[ len( filled_columns ): ] )
    return split.join( filled_columns )


def join_files( filename1, column1, filename2, column2, out_filename, split=None, buffer=1000000, keep_unmatched=False, keep_partial=False, index_depth=3, fill_options=None ):
    # return identifier based upon line
    def get_identifier_by_line( line, column, split=None ):
        if isinstance( line, str ):
            fields = line.rstrip( '\r\n' ).split( split )
            if column < len( fields ):
                return fields[column]
        return None
    if fill_options is None:
        fill_options = Bunch( fill_unjoined_only=True, file1_columns=None, file2_columns=None )
    out = open( out_filename, 'w+b' )
    index = BufferedIndex( filename2, column2, split, buffer, index_depth )
    for line1 in open( filename1, 'rb' ):
        identifier = get_identifier_by_line( line1, column1, split )
        if identifier:
            written = False
            for line2 in index.get_lines_by_identifier( identifier ):
                if not fill_options.fill_unjoined_only:
                    out.write( "%s%s%s\n" % ( fill_empty_columns( line1.rstrip( '\r\n' ), split, fill_options.file1_columns ), split, fill_empty_columns( line2.rstrip( '\r\n' ), split, fill_options.file2_columns ) ) )
                else:
                    out.write( "%s%s%s\n" % ( line1.rstrip( '\r\n' ), split, line2.rstrip( '\r\n' ) ) )
                written = True
            if not written and keep_unmatched:
                out.write( fill_empty_columns( line1.rstrip( '\r\n' ), split, fill_options.file1_columns ) )
                if fill_options:
                    if fill_options.file2_columns:
                        out.write( "%s%s" % ( split, fill_empty_columns( "", split, fill_options.file2_columns ) ) )
                out.write( "\n" )
        elif keep_partial:
            out.write( fill_empty_columns( line1.rstrip( '\r\n' ), split, fill_options.file1_columns ) )
            if fill_options:
                if fill_options.file2_columns:
                    out.write( "%s%s" % ( split, fill_empty_columns( "", split, fill_options.file2_columns ) ) )
            out.write( "\n" )
    out.close()


def main():
    parser = optparse.OptionParser()
    parser.add_option(
        '-b', '--buffer',
        dest='buffer',
        type='int', default=1000000,
        help='Number of lines to buffer at a time. Default: 1,000,000 lines. A buffer of 0 will attempt to use memory only.'
    )
    parser.add_option(
        '-d', '--index_depth',
        dest='index_depth',
        type='int', default=3,
        help='Depth to use on filebased offset indexing. Default: 3.'
    )
    parser.add_option(
        '-p', '--keep_partial',
        action='store_true',
        dest='keep_partial',
        default=False,
        help='Keep rows in first input which are missing identifiers.')
    parser.add_option(
        '-u', '--keep_unmatched',
        action='store_true',
        dest='keep_unmatched',
        default=False,
        help='Keep rows in first input which are not joined with the second input.')
    parser.add_option(
        '-f', '--fill_options_file',
        dest='fill_options_file',
        type='str', default=None,
        help='Fill empty columns with a values from a JSONified file.')

    options, args = parser.parse_args()

    fill_options = None
    if options.fill_options_file is not None:
        try:
            fill_options = Bunch( **stringify_dictionary_keys( json.load( open( options.fill_options_file ) ) ) )  # json.load( open( options.fill_options_file ) )
        except Exception as e:
            print("Warning: Ignoring fill options due to json error (%s)." % e)
    if fill_options is None:
        fill_options = Bunch()
    if 'fill_unjoined_only' not in fill_options:
        fill_options.fill_unjoined_only = True
    if 'file1_columns' not in fill_options:
        fill_options.file1_columns = None
    if 'file2_columns' not in fill_options:
        fill_options.file2_columns = None

    try:
        filename1 = args[0]
        filename2 = args[1]
        column1 = int( args[2] ) - 1
        column2 = int( args[3] ) - 1
        out_filename = args[4]
    except:
        print("Error parsing command line.", file=sys.stderr)
        sys.exit()

    # Character for splitting fields and joining lines
    split = "\t"

    return join_files( filename1, column1, filename2, column2, out_filename, split, options.buffer, options.keep_unmatched, options.keep_partial, options.index_depth, fill_options=fill_options )


if __name__ == "__main__":
    main()
