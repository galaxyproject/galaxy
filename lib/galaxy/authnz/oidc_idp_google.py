"""
Contains implementations for authentication and authorization against Google identity provider.

This package follows "authorization code flow" authentication protocol to authenticate
Galaxy users against third-party identity providers.

"""

import logging
import httplib2
import hashlib
import json
from xml.etree.ElementTree import ParseError
from datetime import datetime
from datetime import timedelta
from ..authnz import IdentityProvider
from oauth2client import client, GOOGLE_TOKEN_URI, GOOGLE_REVOKE_URI


log = logging.getLogger( __name__ )


class OIDCIdPGoogle( IdentityProvider ):
    def __init__( self, config ):
        client_secret_file = config.find( 'client_secret_file' )
        if client_secret_file is None:
            log.error( "Did not find `client_secret_file` key in the configuration; skipping the node '{}'."
                      .format(config.get( 'name' ) ) )
            raise ParseError
        redirect_uri = config.find( 'redirect_uri' )
        if redirect_uri is None:
            log.error( "Did not find `redirect_uri` key in the configuration; skipping the node '{}'."
                      .format(config.get( 'name' ) ) )
            raise ParseError
        self.provider = 'Google'
        self.client_secret_file = client_secret_file.text
        self.redirect_uri = redirect_uri.text

    def _redirect_uri( self, trans ):
        # Prepare authentication flow.
        flow = client.flow_from_clientsecrets(
            self.client_secret_file,
            scope=[ 'openid', 'email', 'profile' ],
            redirect_uri=self.redirect_uri )
        flow.params[ 'access_type' ] = 'offline'  # This asks google to send back a `refresh token`.
        flow.params[ 'prompt' ] = 'consent'

        # Include the following parameter only if we need 'incremental authorization',
        # however, current application scenario does not seem to require it.
        # flow.params[ 'include_granted_scopes' ] = "true"

        # A anti-forgery state token. This token will be sent back from Google upon user authentication.
        state_token = hashlib.sha256( str( trans.user.username ) ).hexdigest()
        flow.params[ 'state' ] = state_token
        user_oauth2 = trans.app.model.UserOAuth2( trans.user.id, self.provider, state_token )
        trans.sa_session.add( user_oauth2 )
        trans.sa_session.flush()
        return flow.step1_get_authorize_url()

    def _refresh_access_token( self, trans, authn_record ):  # TODO: handle `Bad Request` error
        with open( self.client_secret_file ) as file:
            client_secret = json.load( file )[ 'web' ]
            credentials = client.OAuth2Credentials(
                None, client_secret[ 'client_id' ], client_secret[ 'client_secret' ],
                authn_record.refresh_token, None, GOOGLE_TOKEN_URI, None, revoke_uri = GOOGLE_REVOKE_URI )
        credentials.refresh( httplib2.Http() )
        access_token = credentials.get_access_token()
        authn_record.id_token = credentials.id_token_jwt
        authn_record.access_token = access_token[ 'access_token' ]
        authn_record.expiration_date = datetime.now() + timedelta( seconds = access_token[ 'expires_in' ] )
        trans.sa_session.commit()
        trans.sa_session.flush()

    def authenticate( self, trans ):
        query_result = trans.sa_session.query(
            trans.app.model.UserOAuth2).filter(
            trans.app.model.UserOAuth2.table.c.user_id == trans.user.id).filter(
            trans.app.model.UserOAuth2.table.c.provider == self.provider )
        if query_result.count() == 1:
            authn_record = query_result.first()
            if authn_record.expiration_date is not None \
                    and authn_record.expiration_date < datetime.now() + timedelta( minutes = 15 ):
                self._refresh_access_token( trans, authn_record )
        elif query_result.count() > 1:
            log.critical(
                "Found `{}` records for user `{}` authentication against `{}` identity provider; at most one "
                "record should exist. Now deleting all the `{}` records and prompt re-authentication.".format(
                    query_result.count(), trans.user.username, self.provider, query_result.count() ) )
            for record in query_result:
                trans.sa_session.delete( record )
            trans.sa_session.flush()
        return self._redirect_uri( trans )

    def callback( self, state_token, authz_code, trans ):
        query_result = trans.sa_session.query(trans.app.model.UserOAuth2 ).filter(
            trans.app.model.UserOAuth2.table.c.provider == self.provider ).filter(
            trans.app.model.UserOAuth2.table.c.state_token == state_token )
        if query_result.count() > 1:
            log.critical(
                "Found `{}` records for user `{}` authentication against `{}` identity provider; at most one "
                "record should exist. Now deleting all the `{}` records and prompt re-authentication.".format(
                    query_result.count(), trans.user.username, self.provider, query_result.count() ) )
            for record in query_result:
                trans.sa_session.delete( record )
            trans.sa_session.flush()
            return False  # results in re-authentication.
        if query_result.count() == 0:
            log.critical( "Found `0` records for user `{}` authentication against `{}` identity provider;"
                          " an improperly initiated authentication flow. Now prompting re-authentication.".format(
                trans.user.username, self.provider ) )
            return False  # results in re-authentication.
            # A callback should follow a request from Galaxy; and if a request was (successfully) made by Galaxy,
            # the a record in the `galaxy_user_oauth2` table with valid `user_id`, `provider`, and `state_token`
            # should exist (see _redirect_uri function). Since such record does not exist, Galaxy should not
            # trust the token, and does not attempt to associate with a user. Alternatively, we could linearly scan
            # the users table and find a username which creates a `state_token` matching the received `state_token`,
            # but it is safer to retry authentication instead.
        # Prepare authentication flow.
        flow = client.flow_from_clientsecrets(
            self.client_secret_file,
            scope=[ 'openid', 'email', 'profile' ],
            redirect_uri = self.redirect_uri )
        # Exchanges an authorization code for OAuth2Credentials.
        # The credentials object holds refresh and access tokens
        # that authorize access to a single user's data.
        credentials = flow.step2_exchange( authz_code )
        access_token = credentials.get_access_token()
        user_oauth_record = query_result.first()
        user_oauth_record.id_token = credentials.id_token_jwt
        user_oauth_record.refresh_token = credentials.refresh_token
        user_oauth_record.expiration_date = datetime.now() + timedelta( seconds = access_token.expires_in )
        user_oauth_record.access_token = access_token.access_token
        trans.sa_session.flush()
        log.debug( "User `{}` authentication against `Google` identity provider, is successfully saved."
                  .format( trans.user.username ) )
        return True
