# -*- coding: utf-8 -*-
"""
Utility functions used systemwide.

"""

from __future__ import absolute_import

import binascii
import collections
import errno
import grp
import logging
import os
import pickle
import random
import re
import shutil
import smtplib
import stat
import string
import sys
import tempfile
import threading

from galaxy.util import json

from email.MIMEText import MIMEText

from os.path import relpath
from hashlib import md5
from itertools import izip

from urlparse import urlparse

from galaxy import eggs

eggs.require( 'docutils' )
import docutils.core
import docutils.writers.html4css1

eggs.require( 'elementtree' )
from elementtree import ElementTree, ElementInclude

eggs.require( "wchartype" )
import wchartype

from .inflection import Inflector, English
inflector = Inflector(English)

log = logging.getLogger(__name__)
_lock = threading.RLock()

CHUNK_SIZE = 65536  # 64k

DATABASE_MAX_STRING_SIZE = 32768
DATABASE_MAX_STRING_SIZE_PRETTY = '32K'

gzip_magic = '\037\213'
bz2_magic = 'BZh'
DEFAULT_ENCODING = os.environ.get('GALAXY_DEFAULT_ENCODING', 'utf-8')
NULL_CHAR = '\000'
BINARY_CHARS = [ NULL_CHAR ]


def is_multi_byte( chars ):
    for char in chars:
        try:
            char = unicode( char )
        except UnicodeDecodeError:
            # Probably binary
            return False
        if ( wchartype.is_asian( char ) or wchartype.is_full_width( char ) or
             wchartype.is_kanji( char ) or wchartype.is_hiragana( char ) or
             wchartype.is_katakana( char ) or wchartype.is_half_katakana( char )
             or wchartype.is_hangul( char ) or wchartype.is_full_digit( char )
             or wchartype.is_full_letter( char )):
            return True
    return False


def is_binary( value, binary_chars=None ):
    """
    File is binary if it contains a null-byte by default (e.g. behavior of grep, etc.).
    This may fail for utf-16 files, but so would ASCII encoding.
    >>> is_binary( string.printable )
    False
    >>> is_binary( '\\xce\\x94' )
    False
    >>> is_binary( '\\000' )
    True
    """
    if binary_chars is None:
        binary_chars = BINARY_CHARS
    for binary_char in binary_chars:
        if binary_char in value:
            return True
    return False


def is_uuid( value ):
    """
    This method returns True if value is a UUID, otherwise False.
    >>> is_uuid( "123e4567-e89b-12d3-a456-426655440000" )
    True
    >>> is_uuid( "0x3242340298902834" )
    False
    """
    uuid_re = re.compile( "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}" )
    if re.match( uuid_re, str( value ) ):
        return True
    else:
        return False


def get_charset_from_http_headers( headers, default=None ):
    rval = headers.get('content-type', None )
    if rval and 'charset=' in rval:
        rval = rval.split('charset=')[-1].split(';')[0].strip()
        if rval:
            return rval
    return default


def synchronized(func):
    """This wrapper will serialize access to 'func' to a single thread. Use it as a decorator."""
    def caller(*params, **kparams):
        _lock.acquire(True)  # Wait
        try:
            return func(*params, **kparams)
        finally:
            _lock.release()
    return caller


def file_iter(fname, sep=None):
    """
    This generator iterates over a file and yields its lines
    splitted via the C{sep} parameter. Skips empty lines and lines starting with
    the C{#} character.

    >>> lines = [ line for line in file_iter(__file__) ]
    >>> len(lines) !=  0
    True
    """
    for line in file(fname):
        if line and line[0] != '#':
            yield line.split(sep)


def file_reader( fp, chunk_size=CHUNK_SIZE ):
    """This generator yields the open fileobject in chunks (default 64k). Closes the file at the end"""
    while 1:
        data = fp.read(chunk_size)
        if not data:
            break
        yield data
    fp.close()


def unique_id(KEY_SIZE=128):
    """
    Generates an unique id

    >>> ids = [ unique_id() for i in range(1000) ]
    >>> len(set(ids))
    1000
    """
    return md5(str( random.getrandbits( KEY_SIZE ) )).hexdigest()


def parse_xml(fname):
    """Returns a parsed xml tree"""
    tree = ElementTree.parse(fname)
    root = tree.getroot()
    ElementInclude.include(root)
    return tree


def parse_xml_string(xml_string):
    tree = ElementTree.fromstring(xml_string)
    return tree


def xml_to_string( elem, pretty=False ):
    """Returns a string from an xml tree"""
    if pretty:
        elem = pretty_print_xml( elem )
    try:
        return ElementTree.tostring( elem )
    except TypeError, e:
        # we assume this is a comment
        if hasattr( elem, 'text' ):
            return "<!-- %s -->\n" % ( elem.text )
        else:
            raise e


def xml_element_compare( elem1, elem2 ):
    if not isinstance( elem1, dict ):
        elem1 = xml_element_to_dict( elem1 )
    if not isinstance( elem2, dict ):
        elem2 = xml_element_to_dict( elem2 )
    return elem1 == elem2


def xml_element_list_compare( elem_list1, elem_list2 ):
    return [ xml_element_to_dict( elem ) for elem in elem_list1  ] == [ xml_element_to_dict( elem ) for elem in elem_list2  ]


def xml_element_to_dict( elem ):
    rval = {}
    if elem.attrib:
        rval[ elem.tag ] = {}
    else:
        rval[ elem.tag ] = None

    sub_elems = list( elem )
    if sub_elems:
        sub_elem_dict = dict()
        for sub_sub_elem_dict in map( xml_element_to_dict, sub_elems ):
            for key, value in sub_sub_elem_dict.iteritems():
                if key not in sub_elem_dict:
                    sub_elem_dict[ key ] = []
                sub_elem_dict[ key ].append( value )
        for key, value in sub_elem_dict.iteritems():
            if len( value ) == 1:
                rval[ elem.tag ][ key ] = value[0]
            else:
                rval[ elem.tag ][ key ] = value
    if elem.attrib:
        for key, value in elem.attrib.iteritems():
            rval[ elem.tag ][ "@%s" % key ] = value

    if elem.text:
        text = elem.text.strip()
        if text and sub_elems or elem.attrib:
            rval[ elem.tag ][ '#text' ] = text
        else:
            rval[ elem.tag ] = text

    return rval


def pretty_print_xml( elem, level=0 ):
    pad = '    '
    i = "\n" + level * pad
    if len( elem ):
        if not elem.text or not elem.text.strip():
            elem.text = i + pad + pad
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for e in elem:
            pretty_print_xml( e, level + 1 )
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and ( not elem.tail or not elem.tail.strip() ):
            elem.tail = i + pad
    return elem


def get_file_size( value, default=None ):
    try:
        # try built-in
        return os.path.getsize( value )
    except:
        try:
            # try built-in one name attribute
            return os.path.getsize( value.name )
        except:
            try:
                # try tell() of end of object
                offset = value.tell()
                value.seek( 0, 2 )
                rval = value.tell()
                value.seek( offset )
                return rval
            except:
                # return default value
                return default


def shrink_stream_by_size( value, size, join_by="..", left_larger=True, beginning_on_size_error=False, end_on_size_error=False ):
    rval = ''
    if get_file_size( value ) > size:
        start = value.tell()
        len_join_by = len( join_by )
        min_size = len_join_by + 2
        if size < min_size:
            if beginning_on_size_error:
                rval = value.read( size )
                value.seek( start )
                return rval
            elif end_on_size_error:
                value.seek( -size, 2 )
                rval = value.read( size )
                value.seek( start )
                return rval
            raise ValueError( 'With the provided join_by value (%s), the minimum size value is %i.' % ( join_by, min_size ) )
        left_index = right_index = int( ( size - len_join_by ) / 2 )
        if left_index + right_index + len_join_by < size:
            if left_larger:
                left_index += 1
            else:
                right_index += 1
        rval = value.read( left_index ) + join_by
        value.seek( -right_index, 2 )
        rval += value.read( right_index )
    else:
        while True:
            data = value.read( CHUNK_SIZE )
            if not data:
                break
            rval += data
    return rval


def shrink_string_by_size( value, size, join_by="..", left_larger=True, beginning_on_size_error=False, end_on_size_error=False ):
    if len( value ) > size:
        len_join_by = len( join_by )
        min_size = len_join_by + 2
        if size < min_size:
            if beginning_on_size_error:
                return value[:size]
            elif end_on_size_error:
                return value[-size:]
            raise ValueError( 'With the provided join_by value (%s), the minimum size value is %i.' % ( join_by, min_size ) )
        left_index = right_index = int( ( size - len_join_by ) / 2 )
        if left_index + right_index + len_join_by < size:
            if left_larger:
                left_index += 1
            else:
                right_index += 1
        value = "%s%s%s" % ( value[:left_index], join_by, value[-right_index:] )
    return value


def pretty_print_json(json_data, is_json_string=False):
    if is_json_string:
        json_data = json.loads(json_data)
    return json.dumps(json_data, sort_keys=True, indent=4)

# characters that are valid
valid_chars = set(string.letters + string.digits + " -=_.()/+*^,:?!")

# characters that are allowed but need to be escaped
mapped_chars = { '>': '__gt__',
                 '<': '__lt__',
                 "'": '__sq__',
                 '"': '__dq__',
                 '[': '__ob__',
                 ']': '__cb__',
                 '{': '__oc__',
                 '}': '__cc__',
                 '@': '__at__',
                 '\n': '__cn__',
                 '\r': '__cr__',
                 '\t': '__tc__',
                 '#': '__pd__'}


def restore_text(text):
    """Restores sanitized text"""
    if not text:
        return text
    for key, value in mapped_chars.items():
        text = text.replace(value, key)
    return text


def sanitize_text(text):
    """
    Restricts the characters that are allowed in text; accepts both strings
    and lists of strings.
    """
    if isinstance( text, basestring ):
        return _sanitize_text_helper(text)
    elif isinstance( text, list ):
        return [ _sanitize_text_helper(t) for t in text ]


def _sanitize_text_helper(text):
    """Restricts the characters that are allowed in a string"""

    out = []
    for c in text:
        if c in valid_chars:
            out.append(c)
        elif c in mapped_chars:
            out.append(mapped_chars[c])
        else:
            out.append('X')  # makes debugging easier
    return ''.join(out)


def sanitize_param(value):
    """Clean incoming parameters (strings or lists)"""
    if isinstance( value, basestring ):
        return sanitize_text(value)
    elif isinstance( value, list ):
        return map(sanitize_text, value)
    else:
        raise Exception('Unknown parameter type (%s)' % ( type( value ) ))

valid_filename_chars = set( string.ascii_letters + string.digits + '_.' )
invalid_filenames = [ '', '.', '..' ]


def sanitize_for_filename( text, default=None ):
    """
    Restricts the characters that are allowed in a filename portion; Returns default value or a unique id string if result is not a valid name.
    Method is overly aggressive to minimize possible complications, but a maximum length is not considered.
    """
    out = []
    for c in text:
        if c in valid_filename_chars:
            out.append( c )
        else:
            out.append( '_' )
    out = ''.join( out )
    if out in invalid_filenames:
        if default is None:
            return sanitize_for_filename( str( unique_id() ) )
        return default
    return out


def ready_name_for_url( raw_name ):
    """ General method to convert a string (i.e. object name) to a URL-ready
    slug.

    >>> ready_name_for_url( "My Cool Object" )
    'My-Cool-Object'
    >>> ready_name_for_url( "!My Cool Object!" )
    'My-Cool-Object'
    >>> ready_name_for_url( "Hello₩◎ґʟⅾ" )
    'Hello'
    """

    # Replace whitespace with '-'
    slug_base = re.sub( "\s+", "-", raw_name )
    # Remove all non-alphanumeric characters.
    slug_base = re.sub( "[^a-zA-Z0-9\-]", "", slug_base )
    # Remove trailing '-'.
    if slug_base.endswith('-'):
        slug_base = slug_base[:-1]
    return slug_base


def in_directory( file, directory, local_path_module=os.path ):
    """
    Return true, if the common prefix of both is equal to directory
    e.g. /a/b/c/d.rst and directory is /a/b, the common prefix is /a/b
    """

    # Make both absolute.
    directory = local_path_module.abspath(directory)
    file = local_path_module.abspath(file)
    return local_path_module.commonprefix([file, directory]) == directory


def merge_sorted_iterables( operator, *iterables ):
    """

    >>> operator = lambda x: x
    >>> list( merge_sorted_iterables( operator, [1,2,3], [4,5] ) )
    [1, 2, 3, 4, 5]
    >>> list( merge_sorted_iterables( operator, [4, 5], [1,2,3] ) )
    [1, 2, 3, 4, 5]
    >>> list( merge_sorted_iterables( operator, [1, 4, 5], [2], [3] ) )
    [1, 2, 3, 4, 5]
    """
    first_iterable = iterables[ 0 ]
    if len( iterables ) == 1:
        for el in first_iterable:
            yield el
    else:
        for el in __merge_two_sorted_iterables(
            operator,
            iter( first_iterable ),
            merge_sorted_iterables( operator, *iterables[ 1: ] )
        ):
            yield el


def __merge_two_sorted_iterables( operator, iterable1, iterable2 ):
    unset = object()
    continue_merge = True
    next_1 = unset
    next_2 = unset
    while continue_merge:
        try:
            if next_1 is unset:
                next_1 = next( iterable1 )
            if next_2 is unset:
                next_2 = next( iterable2 )
            if operator( next_2 ) < operator( next_1 ):
                yield next_2
                next_2 = unset
            else:
                yield next_1
                next_1 = unset
        except StopIteration:
            continue_merge = False
    if next_1 is not unset:
        yield next_1
    if next_2 is not unset:
        yield next_2
    for el in iterable1:
        yield el
    for el in iterable2:
        yield el


class Params( object ):
    """
    Stores and 'sanitizes' parameters. Alphanumeric characters and the
    non-alphanumeric ones that are deemed safe are let to pass through (see L{valid_chars}).
    Some non-safe characters are escaped to safe forms for example C{>} becomes C{__lt__}
    (see L{mapped_chars}). All other characters are replaced with C{X}.

    Operates on string or list values only (HTTP parameters).

    >>> values = { 'status':'on', 'symbols':[  'alpha', '<>', '$rm&#!' ]  }
    >>> par = Params(values)
    >>> par.status
    'on'
    >>> par.value == None      # missing attributes return None
    True
    >>> par.get('price', 0)
    0
    >>> par.symbols            # replaces unknown symbols with X
    ['alpha', '__lt____gt__', 'XrmX__pd__!']
    >>> par.flatten()          # flattening to a list
    [('status', 'on'), ('symbols', 'alpha'), ('symbols', '__lt____gt__'), ('symbols', 'XrmX__pd__!')]
    """

    # is NEVER_SANITIZE required now that sanitizing for tool parameters can be controlled on a per parameter basis and occurs via InputValueWrappers?
    NEVER_SANITIZE = ['file_data', 'url_paste', 'URL', 'filesystem_paths']

    def __init__( self, params, sanitize=True ):
        if sanitize:
            for key, value in params.items():
                if key not in self.NEVER_SANITIZE and True not in [ key.endswith( "|%s" % nonsanitize_parameter ) for nonsanitize_parameter in self.NEVER_SANITIZE ]:  # sanitize check both ungrouped and grouped parameters by name. Anything relying on NEVER_SANITIZE should be changed to not require this and NEVER_SANITIZE should be removed.
                    self.__dict__[ key ] = sanitize_param( value )
                else:
                    self.__dict__[ key ] = value
        else:
            self.__dict__.update(params)

    def flatten(self):
        """
        Creates a tuple list from a dict with a tuple/value pair for every value that is a list
        """
        flat = []
        for key, value in self.__dict__.items():
            if isinstance(value, list):
                for v in value:
                    flat.append( (key, v) )
            else:
                flat.append( (key, value) )
        return flat

    def __getattr__(self, name):
        """This is here to ensure that we get None for non existing parameters"""
        return None

    def get(self, key, default):
        return self.__dict__.get(key, default)

    def __str__(self):
        return '%s' % self.__dict__

    def __len__(self):
        return len(self.__dict__)

    def __iter__(self):
        return iter(self.__dict__)

    def update(self, values):
        self.__dict__.update(values)


def rst_to_html( s ):
    """Convert a blob of reStructuredText to HTML"""
    log = logging.getLogger( "docutils" )

    class FakeStream( object ):
        def write( self, str ):
            if len( str ) > 0 and not str.isspace():
                log.warn( str )
    return unicodify( docutils.core.publish_string( s,
                      writer=docutils.writers.html4css1.Writer(),
                      settings_overrides={ "embed_stylesheet": False, "template": os.path.join(os.path.dirname(__file__), "docutils_template.txt"), "warning_stream": FakeStream() } ) )


def xml_text(root, name=None):
    """Returns the text inside an element"""
    if name is not None:
        # Try attribute first
        val = root.get(name)
        if val:
            return val
        # Then try as element
        elem = root.find(name)
    else:
        elem = root
    if elem is not None and elem.text:
        text = ''.join(elem.text.splitlines())
        return text.strip()
    # No luck, return empty string
    return ''

# asbool implementation pulled from PasteDeploy
truthy = frozenset(['true', 'yes', 'on', 'y', 't', '1'])
falsy = frozenset(['false', 'no', 'off', 'n', 'f', '0'])


def asbool(obj):
    if isinstance(obj, basestring):
        obj = obj.strip().lower()
        if obj in truthy:
            return True
        elif obj in falsy:
            return False
        else:
            raise ValueError("String is not true/false: %r" % obj)
    return bool(obj)


def string_as_bool( string ):
    if str( string ).lower() in ( 'true', 'yes', 'on' ):
        return True
    else:
        return False


def string_as_bool_or_none( string ):
    """
    Returns True, None or False based on the argument:
        True if passed True, 'True', 'Yes', or 'On'
        None if passed None or 'None'
        False otherwise

    Note: string comparison is case-insensitive so lowecase versions of those
    function equivalently.
    """
    string = str( string ).lower()
    if string in ( 'true', 'yes', 'on' ):
        return True
    elif string == 'none':
        return None
    else:
        return False


def listify( item, do_strip=False ):
    """
    Make a single item a single item list, or return a list if passed a
    list.  Passing a None returns an empty list.
    """
    if not item:
        return []
    elif isinstance( item, list ):
        return item
    elif isinstance( item, basestring ) and item.count( ',' ):
        if do_strip:
            return [token.strip() for token in item.split( ',' )]
        else:
            return item.split( ',' )
    else:
        return [ item ]


def commaify(amount):
    orig = amount
    new = re.sub("^(-?\d+)(\d{3})", '\g<1>,\g<2>', amount)
    if orig == new:
        return new
    else:
        return commaify(new)


def roundify(amount, sfs=2):
    """
    Take a number in string form and truncate to 'sfs' significant figures.
    """
    if len(amount) <= sfs:
        return amount
    else:
        return amount[0:sfs] + '0'*(len(amount) - sfs)


def unicodify( value, encoding=DEFAULT_ENCODING, error='replace', default=None ):
    """
    Returns a unicode string or None
    """

    if isinstance( value, unicode ):
        return value
    try:
        return unicode( str( value ), encoding, error )
    except:
        return default


def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.

    Adapted from an older, simpler version of django.utils.encoding.smart_str.
    """
    if strings_only and isinstance(s, (type(None), int)):
        return s
    if not isinstance(s, basestring):
        try:
            return str(s)
        except UnicodeEncodeError:
            return unicode(s).encode(encoding, errors)
    elif isinstance(s, unicode):
        return s.encode(encoding, errors)
    elif s and encoding != 'utf-8':
        return s.decode('utf-8', errors).encode(encoding, errors)
    else:
        return s


def object_to_string( obj ):
    return binascii.hexlify( obj )


def string_to_object( s ):
    return binascii.unhexlify( s )


class ParamsWithSpecs( collections.defaultdict ):
    """
    """

    def __init__( self, specs=None, params=None ):
        self.specs = specs or dict()
        self.params = params or dict()
        for name, value in self.params.items():
            if name not in self.specs:
                self._param_unknown_error( name )
            if 'map' in self.specs[ name ]:
                try:
                    self.params[ name ] = self.specs[ name ][ 'map' ]( value )
                except Exception:
                    self._param_map_error( name, value )
            if 'valid' in self.specs[ name ]:
                if not self.specs[ name ][ 'valid' ]( value ):
                    self._param_vaildation_error( name, value )

        self.update( self.params )

    def __missing__( self, name ):
        return self.specs[ name ][ 'default' ]

    def __getattr__( self, name ):
        return self[ name ]

    def _param_unknown_error( self, name ):
        raise NotImplementedError()

    def _param_map_error( self, name, value ):
        raise NotImplementedError()

    def _param_vaildation_error( self, name, value ):
        raise NotImplementedError()


def compare_urls( url1, url2, compare_scheme=True, compare_hostname=True, compare_path=True ):
    url1 = urlparse( url1 )
    url2 = urlparse( url2 )
    if compare_scheme and url1.scheme and url2.scheme and url1.scheme != url2.scheme:
        return False
    if compare_hostname and url1.hostname and url2.hostname and url1.hostname != url2.hostname:
        return False
    if compare_path and url1.path and url2.path and url1.path != url2.path:
        return False
    return True


def read_dbnames(filename):
    """ Read build names from file """
    class DBNames( list ):
        default_value = "?"
        default_name = "unspecified (?)"
    db_names = DBNames()
    try:
        ucsc_builds = {}
        man_builds = []  # assume these are integers
        name_to_db_base = {}
        if filename is None:
            # Should only be happening with the galaxy.tools.parameters.basic:GenomeBuildParameter docstring unit test
            filename = os.path.join( 'tool-data', 'shared', 'ucsc', 'builds.txt.sample' )
        for line in open(filename):
            try:
                if line[0:1] == "#":
                    continue
                fields = line.replace("\r", "").replace("\n", "").split("\t")
                # Special case of unspecified build is at top of list
                if fields[0] == "?":
                    db_names.insert(0, (fields[0], fields[1]))
                    continue
                try:  # manual build (i.e. microbes)
                    int(fields[0])
                    man_builds.append((fields[1], fields[0]))
                except:  # UCSC build
                    db_base = fields[0].rstrip('0123456789')
                    if db_base not in ucsc_builds:
                        ucsc_builds[db_base] = []
                        name_to_db_base[fields[1]] = db_base
                    # we want to sort within a species numerically by revision number
                    build_rev = re.compile(r'\d+$')
                    try:
                        build_rev = int(build_rev.findall(fields[0])[0])
                    except:
                        build_rev = 0
                    ucsc_builds[db_base].append((build_rev, fields[0], fields[1]))
            except:
                continue
        sort_names = name_to_db_base.keys()
        sort_names.sort()
        for name in sort_names:
            db_base = name_to_db_base[name]
            ucsc_builds[db_base].sort()
            ucsc_builds[db_base].reverse()
            ucsc_builds[db_base] = [(build, name) for _, build, name in ucsc_builds[db_base]]
            db_names = DBNames( db_names + ucsc_builds[db_base] )
        if len( db_names ) > 1 and len( man_builds ) > 0:
            db_names.append( ( db_names.default_value, '----- Additional Species Are Below -----' ) )
        man_builds.sort()
        man_builds = [(build, name) for name, build in man_builds]
        db_names = DBNames( db_names + man_builds )
    except Exception, e:
        print "ERROR: Unable to read builds file:", e
    if len(db_names) < 1:
        db_names = DBNames( [( db_names.default_value,  db_names.default_name )] )
    return db_names


def read_build_sites( filename, check_builds=True ):
    """ read db names to ucsc mappings from file, this file should probably be merged with the one above """
    build_sites = []
    try:
        for line in open(filename):
            try:
                if line[0:1] == "#":
                    continue
                fields = line.replace("\r", "").replace("\n", "").split("\t")
                site_name = fields[0]
                site = fields[1]
                if check_builds:
                    site_builds = fields[2].split(",")
                    site_dict = {'name': site_name, 'url': site, 'builds': site_builds}
                else:
                    site_dict = {'name': site_name, 'url': site}
                build_sites.append( site_dict )
            except:
                continue
    except:
        print "ERROR: Unable to read builds for site file %s" % filename
    return build_sites


def relativize_symlinks( path, start=None, followlinks=False):
    for root, dirs, files in os.walk( path, followlinks=followlinks ):
        rel_start = None
        for file_name in files:
            symlink_file_name = os.path.join( root, file_name )
            if os.path.islink( symlink_file_name ):
                symlink_target = os.readlink( symlink_file_name )
                if rel_start is None:
                    if start is None:
                        rel_start = root
                    else:
                        rel_start = start
                rel_path = relpath( symlink_target, rel_start )
                os.remove( symlink_file_name )
                os.symlink( rel_path, symlink_file_name )


def stringify_dictionary_keys( in_dict ):
    # returns a new dictionary
    # changes unicode keys into strings, only works on top level (does not recurse)
    # unicode keys are not valid for expansion into keyword arguments on method calls
    out_dict = {}
    for key, value in in_dict.iteritems():
        out_dict[ str( key ) ] = value
    return out_dict


def recursively_stringify_dictionary_keys( d ):
    if isinstance(d, dict):
        return dict([(k.encode( DEFAULT_ENCODING ), recursively_stringify_dictionary_keys(v)) for k, v in d.iteritems()])
    elif isinstance(d, list):
        return [recursively_stringify_dictionary_keys(x) for x in d]
    else:
        return d


def mkstemp_ln( src, prefix='mkstemp_ln_' ):
    """
    From tempfile._mkstemp_inner, generate a hard link in the same dir with a
    random name.  Created so we can persist the underlying file of a
    NamedTemporaryFile upon its closure.
    """
    dir = os.path.dirname(src)
    names = tempfile._get_candidate_names()
    for seq in xrange(tempfile.TMP_MAX):
        name = names.next()
        file = os.path.join(dir, prefix + name)
        try:
            os.link( src, file )
            return (os.path.abspath(file))
        except OSError, e:
            if e.errno == errno.EEXIST:
                continue  # try again
            raise
    raise IOError(errno.EEXIST, "No usable temporary file name found")


def umask_fix_perms( path, umask, unmasked_perms, gid=None ):
    """
    umask-friendly permissions fixing
    """
    perms = unmasked_perms & ~umask
    try:
        st = os.stat( path )
    except OSError, e:
        log.exception( 'Unable to set permissions or group on %s' % path )
        return
    # fix modes
    if stat.S_IMODE( st.st_mode ) != perms:
        try:
            os.chmod( path, perms )
        except Exception, e:
            log.warning( 'Unable to honor umask (%s) for %s, tried to set: %s but mode remains %s, error was: %s' % ( oct( umask ),
                                                                                                                      path,
                                                                                                                      oct( perms ),
                                                                                                                      oct( stat.S_IMODE( st.st_mode ) ),
                                                                                                                      e ) )
    # fix group
    if gid is not None and st.st_gid != gid:
        try:
            os.chown( path, -1, gid )
        except Exception, e:
            try:
                desired_group = grp.getgrgid( gid )
                current_group = grp.getgrgid( st.st_gid )
            except:
                desired_group = gid
                current_group = st.st_gid
            log.warning( 'Unable to honor primary group (%s) for %s, group remains %s, error was: %s' % ( desired_group,
                                                                                                          path,
                                                                                                          current_group,
                                                                                                          e ) )


def docstring_trim(docstring):
    """Trimming python doc strings. Taken from: http://www.python.org/dev/peps/pep-0257/"""
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxint
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxint:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)


def nice_size(size):
    """
    Returns a readably formatted string with the size

    >>> nice_size(100)
    '100 bytes'
    >>> nice_size(10000)
    '9.8 KB'
    >>> nice_size(1000000)
    '976.6 KB'
    >>> nice_size(100000000)
    '95.4 MB'
    """
    words = [ 'bytes', 'KB', 'MB', 'GB', 'TB' ]
    try:
        size = float( size )
    except:
        return '??? bytes'
    for ind, word in enumerate(words):
        step = 1024 ** (ind + 1)
        if step > size:
            size = size / float(1024 ** ind)
            if word == 'bytes':  # No decimals for bytes
                return "%d bytes" % size
            return "%.1f %s" % (size, word)
    return '??? bytes'


def size_to_bytes( size ):
    """
    Returns a number of bytes if given a reasonably formatted string with the size
    """
    # Assume input in bytes if we can convert directly to an int
    try:
        return int( size )
    except:
        pass
    # Otherwise it must have non-numeric characters
    size_re = re.compile( '([\d\.]+)\s*([tgmk]b?|b|bytes?)$' )
    size_match = re.match( size_re, size.lower() )
    assert size_match is not None
    size = float( size_match.group(1) )
    multiple = size_match.group(2)
    if multiple.startswith( 't' ):
        return int( size * 1024**4 )
    elif multiple.startswith( 'g' ):
        return int( size * 1024**3 )
    elif multiple.startswith( 'm' ):
        return int( size * 1024**2 )
    elif multiple.startswith( 'k' ):
        return int( size * 1024 )
    elif multiple.startswith( 'b' ):
        return int( size )


def send_mail( frm, to, subject, body, config ):
    """
    Sends an email.
    """
    to = listify( to )
    msg = MIMEText(  body.encode( 'ascii', 'replace' ) )
    msg[ 'To' ] = ', '.join( to )
    msg[ 'From' ] = frm
    msg[ 'Subject' ] = subject
    if config.smtp_server is None:
        log.error( "Mail is not configured for this Galaxy instance." )
        log.info( msg )
        return
    smtp_ssl = asbool( getattr(config, 'smtp_ssl', False ) )
    if smtp_ssl:
        s = smtplib.SMTP_SSL()
    else:
        s = smtplib.SMTP()
    s.connect( config.smtp_server )
    if not smtp_ssl:
        try:
            s.starttls()
            log.debug( 'Initiated SSL/TLS connection to SMTP server: %s' % config.smtp_server )
        except RuntimeError, e:
            log.warning( 'SSL/TLS support is not available to your Python interpreter: %s' % e )
        except smtplib.SMTPHeloError, e:
            log.error( "The server didn't reply properly to the HELO greeting: %s" % e )
            s.close()
            raise
        except smtplib.SMTPException, e:
            log.warning( 'The server does not support the STARTTLS extension: %s' % e )
    if config.smtp_username and config.smtp_password:
        try:
            s.login( config.smtp_username, config.smtp_password )
        except smtplib.SMTPHeloError, e:
            log.error( "The server didn't reply properly to the HELO greeting: %s" % e )
            s.close()
            raise
        except smtplib.SMTPAuthenticationError, e:
            log.error( "The server didn't accept the username/password combination: %s" % e )
            s.close()
            raise
        except smtplib.SMTPException, e:
            log.error( "No suitable authentication method was found: %s" % e )
            s.close()
            raise
    s.sendmail( frm, to, msg.as_string() )
    s.quit()


def force_symlink( source, link_name ):
    try:
        os.symlink( source, link_name )
    except OSError, e:
        if e.errno == errno.EEXIST:
            os.remove( link_name )
            os.symlink( source, link_name )
        else:
            raise e


def move_merge( source, target ):
    # when using shutil and moving a directory, if the target exists,
    # then the directory is placed inside of it
    # if the target doesn't exist, then the target is made into the directory
    # this makes it so that the target is always the target, and if it exists,
    # the source contents are moved into the target
    if os.path.isdir( source ) and os.path.exists( target ) and os.path.isdir( target ):
        for name in os.listdir( source ):
            move_merge( os.path.join( source, name ), os.path.join( target, name ) )
    else:
        return shutil.move( source, target )


def safe_str_cmp(a, b):
    if len(a) != len(b):
        return False
    rv = 0
    for x, y in izip(a, b):
        rv |= ord(x) ^ ord(y)
    return rv == 0

galaxy_root_path = os.path.join(__path__[0], "..", "..", "..")


def galaxy_directory():
    return os.path.abspath(galaxy_root_path)

if __name__ == '__main__':
    import doctest
    doctest.testmod(sys.modules[__name__], verbose=False)
