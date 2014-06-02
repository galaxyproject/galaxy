import collections
import os
import os.path
import logging

import pkg_resources
pkg_resources.require( "pycrypto" )

from Crypto.Cipher import Blowfish
from Crypto.Util.randpool import RandomPool
from Crypto.Util import number

log = logging.getLogger( __name__ )

if os.path.exists( "/dev/urandom" ):
    # We have urandom, use it as the source of random data
    random_fd = os.open( "/dev/urandom", os.O_RDONLY )

    def get_random_bytes( nbytes ):
        value = os.read( random_fd, nbytes )
        # Normally we should get as much as we need
        if len( value ) == nbytes:
            return value.encode( "hex" )
        # If we don't, keep reading (this is slow and should never happen)
        while len( value ) < nbytes:
            value += os.read( random_fd, nbytes - len( value ) )
        return value.encode( "hex" )
else:
    def get_random_bytes( nbytes ):
        nbits = nbytes * 8
        random_pool = RandomPool( 1064 )
        while random_pool.entropy < nbits:
            random_pool.add_event()
        random_pool.stir()
        return str( number.getRandomNumber( nbits, random_pool.get_bytes ) )


class SecurityHelper( object ):

    def __init__( self, **config ):
        self.id_secret = config['id_secret']
        self.id_cipher = Blowfish.new( self.id_secret )

        per_kind_id_secret_base = config.get( 'per_kind_id_secret_base', self.id_secret )
        self.id_ciphers_for_kind = _cipher_cache( per_kind_id_secret_base )

    def encode_id( self, obj_id, kind=None ):
        id_cipher = self.__id_cipher( kind )
        # Convert to string
        s = str( obj_id )
        # Pad to a multiple of 8 with leading "!"
        s = ( "!" * ( 8 - len(s) % 8 ) ) + s
        # Encrypt
        return id_cipher.encrypt( s ).encode( 'hex' )

    def encode_dict_ids( self, a_dict, kind=None ):
        """
        Encode all ids in dictionary. Ids are identified by (a) an 'id' key or
        (b) a key that ends with '_id'
        """
        for key, val in a_dict.items():
            if key == 'id' or key.endswith('_id'):
                a_dict[ key ] = self.encode_id( val, kind=kind )

        return a_dict

    def encode_all_ids( self, rval, recursive=False ):
        """
        Encodes all integer values in the dict rval whose keys are 'id' or end
        with '_id' excluding `tool_id` which are consumed and produced as is
        via the API.
        """
        if not isinstance( rval, dict ):
            return rval
        for k, v in rval.items():
            if ( k == 'id' or k.endswith( '_id' ) ) and v is not None and k not in [ 'tool_id' ]:
                try:
                    rval[ k ] = self.encode_id( v )
                except Exception:
                    pass  # probably already encoded
            if ( k.endswith( "_ids" ) and isinstance( v, list ) ):
                try:
                    o = []
                    for i in v:
                        o.append( self.encode_id( i ) )
                    rval[ k ] = o
                except Exception:
                    pass
            else:
                if recursive and isinstance( v, dict ):
                    rval[ k ] = self.encode_all_ids( v, recursive )
                elif recursive and isinstance( v, list ):
                    rval[ k ] = map( lambda el: self.encode_all_ids( el, True), v )
        return rval

    def decode_id( self, obj_id, kind=None ):
        id_cipher = self.__id_cipher( kind )
        return int( id_cipher.decrypt( obj_id.decode( 'hex' ) ).lstrip( "!" ) )

    def encode_guid( self, session_key ):
        # Session keys are strings
        # Pad to a multiple of 8 with leading "!"
        s = ( "!" * ( 8 - len( session_key ) % 8 ) ) + session_key
        # Encrypt
        return self.id_cipher.encrypt( s ).encode( 'hex' )

    def decode_guid( self, session_key ):
        # Session keys are strings
        return self.id_cipher.decrypt( session_key.decode( 'hex' ) ).lstrip( "!" )

    def get_new_guid( self ):
        # Generate a unique, high entropy 128 bit random number
        return get_random_bytes( 16 )

    def __id_cipher( self, kind ):
        if not kind:
            id_cipher = self.id_cipher
        else:
            id_cipher = self.id_ciphers_for_kind[ kind ]
        return id_cipher


class _cipher_cache( collections.defaultdict ):

    def __init__( self, secret_base ):
        self.secret_base = secret_base

    def __missing__( self, key ):
        return Blowfish.new( self.secret_base + "__" + key )
