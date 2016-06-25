"""
Contains OpenID provider functionality
"""

import os
import logging
from galaxy.util import parse_xml, string_as_bool
from galaxy.util.odict import odict


log = logging.getLogger( __name__ )

NO_PROVIDER_ID = 'None'
RESERVED_PROVIDER_IDS = [ NO_PROVIDER_ID ]


class OpenIDProvider( object ):
    '''An OpenID Provider object.'''
    @classmethod
    def from_file( cls, filename ):
        return cls.from_elem( parse_xml( filename ).getroot() )

    @classmethod
    def from_elem( cls, xml_root ):
        provider_elem = xml_root
        provider_id = provider_elem.get( 'id', None )
        provider_name = provider_elem.get( 'name', provider_id )
        op_endpoint_url = provider_elem.find( 'op_endpoint_url' )
        if op_endpoint_url is not None:
            op_endpoint_url = op_endpoint_url.text
        never_associate_with_user = string_as_bool( provider_elem.get( 'never_associate_with_user', 'False' ) )
        assert (provider_id and provider_name and op_endpoint_url), Exception( "OpenID Provider improperly configured" )
        assert provider_id not in RESERVED_PROVIDER_IDS, Exception( 'Specified OpenID Provider uses a reserved id: %s' % ( provider_id ) )
        sreg_required = []
        sreg_optional = []
        use_for = {}
        store_user_preference = {}
        use_default_sreg = True
        for elem in provider_elem.findall( 'sreg' ):
            use_default_sreg = False
            for field_elem in elem.findall( 'field' ):
                sreg_name = field_elem.get( 'name' )
                assert sreg_name, Exception( 'A name is required for a sreg element' )
                if string_as_bool( field_elem.get( 'required' ) ):
                    sreg_required.append( sreg_name )
                else:
                    sreg_optional.append( sreg_name )
                for use_elem in field_elem.findall( 'use_for' ):
                    use_for[ use_elem.get( 'name' ) ] = sreg_name
                for store_user_preference_elem in field_elem.findall( 'store_user_preference' ):
                    store_user_preference[ store_user_preference_elem.get( 'name' ) ] = sreg_name
        if use_default_sreg:
            sreg_required = None
            sreg_optional = None
            use_for = None
        return cls( provider_id, provider_name, op_endpoint_url, sreg_required=sreg_required, sreg_optional=sreg_optional, use_for=use_for, store_user_preference=store_user_preference, never_associate_with_user=never_associate_with_user )

    def __init__( self, id, name, op_endpoint_url, sreg_required=None, sreg_optional=None, use_for=None, store_user_preference=None, never_associate_with_user=None ):
        '''When sreg options are not specified, defaults are used.'''
        self.id = id
        self.name = name
        self.op_endpoint_url = op_endpoint_url
        if sreg_optional is None:
            self.sreg_optional = [ 'nickname', 'email' ]
        else:
            self.sreg_optional = sreg_optional
        if sreg_required:
            self.sreg_required = sreg_required
        else:
            self.sreg_required = []
        if use_for is not None:
            self.use_for = use_for
        else:
            self.use_for = {}
            if 'nickname' in ( self.sreg_optional + self.sreg_required ):
                self.use_for[ 'username' ] = 'nickname'
            if 'email' in ( self.sreg_optional + self.sreg_required ):
                self.use_for[ 'email' ] = 'email'
        if store_user_preference:
            self.store_user_preference = store_user_preference
        else:
            self.store_user_preference = {}
        if never_associate_with_user:
            self.never_associate_with_user = True
        else:
            self.never_associate_with_user = False

    def post_authentication( self, trans, openid_manager, info ):
        sreg_attributes = openid_manager.get_sreg( info )
        for store_pref_name, store_pref_value_name in self.store_user_preference.iteritems():
            if store_pref_value_name in ( self.sreg_optional + self.sreg_required ):
                trans.user.preferences[ store_pref_name ] = sreg_attributes.get( store_pref_value_name )
            else:
                raise Exception( 'Only sreg is currently supported.' )
        trans.sa_session.add( trans.user )
        trans.sa_session.flush()

    def has_post_authentication_actions( self ):
        return bool( self.store_user_preference )


class OpenIDProviders( object ):
    '''Collection of OpenID Providers'''
    NO_PROVIDER_ID = NO_PROVIDER_ID

    @classmethod
    def from_file( cls, filename ):
        try:
            return cls.from_elem( parse_xml( filename ).getroot() )
        except Exception as e:
            log.error( 'Failed to load OpenID Providers: %s' % ( e ) )
            return cls()

    @classmethod
    def from_elem( cls, xml_root ):
        oid_elem = xml_root
        providers = odict()
        for elem in oid_elem.findall( 'provider' ):
            try:
                provider = OpenIDProvider.from_file( os.path.join( 'openid', elem.get( 'file' ) ) )
                providers[ provider.id ] = provider
                log.debug( 'Loaded OpenID provider: %s (%s)' % ( provider.name, provider.id ) )
            except Exception as e:
                log.error( 'Failed to add OpenID provider: %s' % ( e ) )
        return cls( providers )

    def __init__( self, providers=None ):
        if providers:
            self.providers = providers
        else:
            self.providers = odict()
        self._banned_identifiers = [ provider.op_endpoint_url for provider in self.providers.itervalues() if provider.never_associate_with_user ]

    def __iter__( self ):
        for provider in self.providers.itervalues():
            yield provider

    def get( self, name, default=None ):
        if name in self.providers:
            return self.providers[ name ]
        else:
            return default

    def new_provider_from_identifier( self, identifier ):
        return OpenIDProvider( None, identifier, identifier, never_associate_with_user=identifier in self._banned_identifiers )
