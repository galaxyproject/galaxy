"""
Contains the user interface in the Universe class
"""

import glob
import logging
import os
import socket
import string
import random
import urllib
from galaxy import web
from galaxy import util
from galaxy import model
from galaxy.model.orm import and_
from galaxy.security.validate_user_input import validate_email
from galaxy.security.validate_user_input import validate_publicname
from galaxy.security.validate_user_input import validate_password
from galaxy.security.validate_user_input import transform_publicname
from galaxy.util.json import loads
from galaxy.util.json import dumps
from galaxy.util import listify
from galaxy.util import docstring_trim
from galaxy.web import url_for
from galaxy.web.base.controller import BaseUIController
from galaxy.web.base.controller import UsesFormDefinitionsMixin
from galaxy.web.base.controller import CreatesUsersMixin
from galaxy.web.base.controller import CreatesApiKeysMixin
from galaxy.web.form_builder import CheckboxField
from galaxy.web.form_builder import build_select_field
from galaxy.web.framework.helpers import time_ago, grids
from datetime import datetime, timedelta
from galaxy.util import hash_util, biostar

log = logging.getLogger( __name__ )

require_login_template = """
<p>
    This %s has been configured such that only users who are logged in may use it.%s
</p>
<p/>
"""


class UserOpenIDGrid( grids.Grid ):
    use_panels = False
    title = "OpenIDs linked to your account"
    model_class = model.UserOpenID
    template = '/user/openid_manage.mako'
    default_filter = { "openid": "All" }
    default_sort_key = "-create_time"
    columns = [
        grids.TextColumn( "OpenID URL", key="openid", link=( lambda x: dict( action='openid_auth', login_button="Login", openid_url=x.openid if not x.provider else '', openid_provider=x.provider, auto_associate=True ) ) ),
        grids.GridColumn( "Created", key="create_time", format=time_ago ),
    ]
    operations = [
        grids.GridOperation( "Delete", async_compatible=True ),
    ]

    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( self.model_class ).filter( self.model_class.user_id == trans.user.id )


class User( BaseUIController, UsesFormDefinitionsMixin, CreatesUsersMixin, CreatesApiKeysMixin ):
    user_openid_grid = UserOpenIDGrid()
    installed_len_files = None

    @web.expose
    def index( self, trans, cntrller, **kwd ):
        return trans.fill_template( '/user/index.mako', cntrller=cntrller )

    @web.expose
    def openid_auth( self, trans, **kwd ):
        '''Handles user request to access an OpenID provider'''
        if not trans.app.config.enable_openid:
            return trans.show_error_message( 'OpenID authentication is not enabled in this instance of Galaxy' )
        message = 'Unspecified failure authenticating via OpenID'
        openid_url = kwd.get( 'openid_url', '' )
        openid_provider = kwd.get( 'openid_provider', '' )
        if not openid_provider or openid_url:
            openid_provider = trans.app.openid_providers.NO_PROVIDER_ID  # empty fields cause validation errors
        redirect = kwd.get( 'redirect', '' ).strip()
        auto_associate = util.string_as_bool( kwd.get( 'auto_associate', False ) )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        action = 'login'
        consumer = trans.app.openid_manager.get_consumer( trans )
        if openid_url:
            openid_provider_obj = trans.app.openid_providers.new_provider_from_identifier( openid_url )
        else:
            openid_provider_obj = trans.app.openid_providers.get( openid_provider )
        if not openid_url and openid_provider == trans.app.openid_providers.NO_PROVIDER_ID:
            message = 'An OpenID provider was not specified'
        elif openid_provider_obj:
            if not redirect:
                redirect = ' '
            process_url = trans.request.base.rstrip( '/' ) + url_for( controller='user', action='openid_process', redirect=redirect, openid_provider=openid_provider, auto_associate=auto_associate )  # None of these values can be empty, or else a verification error will occur
            request = None
            try:
                request = consumer.begin( openid_provider_obj.op_endpoint_url )
                if request is None:
                    message = 'No OpenID services are available at %s' % openid_provider_obj.op_endpoint_url
            except Exception, e:
                message = 'Failed to begin OpenID authentication: %s' % str( e )
            if request is not None:
                trans.app.openid_manager.add_sreg( trans, request, required=openid_provider_obj.sreg_required, optional=openid_provider_obj.sreg_optional )
                if request.shouldSendRedirect():
                    redirect_url = request.redirectURL(
                        trans.request.base, process_url )
                    trans.app.openid_manager.persist_session( trans, consumer )
                    return trans.response.send_redirect( redirect_url )
                else:
                    form = request.htmlMarkup( trans.request.base, process_url, form_tag_attrs={'id': 'openid_message', 'target': '_top'} )
                    trans.app.openid_manager.persist_session( trans, consumer )
                    return form
        return trans.response.send_redirect( url_for( controller='user',
                                                      action=action,
                                                      redirect=redirect,
                                                      use_panels=use_panels,
                                                      message=message,
                                                      status='error' ) )

    @web.expose
    def openid_process( self, trans, **kwd ):
        '''Handle's response from OpenID Providers'''
        if not trans.app.config.enable_openid:
            return trans.show_error_message( 'OpenID authentication is not enabled in this instance of Galaxy' )
        auto_associate = util.string_as_bool( kwd.get( 'auto_associate', False ) )
        action = 'login'
        if trans.user:
            action = 'openid_manage'
        if trans.app.config.support_url is not None:
            contact = '<a href="%s">support</a>' % trans.app.config.support_url
        else:
            contact = 'support'
        message = 'Verification failed for an unknown reason.  Please contact %s for assistance.' % ( contact )
        status = 'error'
        consumer = trans.app.openid_manager.get_consumer( trans )
        info = consumer.complete( kwd, trans.request.url )
        display_identifier = info.getDisplayIdentifier()
        redirect = kwd.get( 'redirect', '' ).strip()
        openid_provider = kwd.get( 'openid_provider', None )
        if info.status == trans.app.openid_manager.FAILURE and display_identifier:
            message = "Login via OpenID failed.  The technical reason for this follows, please include this message in your email if you need to %s to resolve this problem: %s" % ( contact, info.message )
            return trans.response.send_redirect( url_for( controller='user',
                                                          action=action,
                                                          use_panels=True,
                                                          redirect=redirect,
                                                          message=message,
                                                          status='error' ) )
        elif info.status == trans.app.openid_manager.SUCCESS:
            if info.endpoint.canonicalID:
                display_identifier = info.endpoint.canonicalID
            openid_provider_obj = trans.app.openid_providers.get( openid_provider )
            user_openid = trans.sa_session.query( trans.app.model.UserOpenID ).filter( trans.app.model.UserOpenID.table.c.openid == display_identifier ).first()
            if not openid_provider_obj and user_openid and user_openid.provider:
                openid_provider_obj = trans.app.openid_providers.get( user_openid.provider )
            if not openid_provider_obj:
                openid_provider_obj = trans.app.openid_providers.new_provider_from_identifier( display_identifier )
            if not user_openid:
                user_openid = trans.app.model.UserOpenID( session=trans.galaxy_session, openid=display_identifier )
            if not user_openid.user:
                user_openid.session = trans.galaxy_session
            if not user_openid.provider and openid_provider:
                user_openid.provider = openid_provider
            if trans.user:
                if user_openid.user and user_openid.user.id != trans.user.id:
                    message = "The OpenID <strong>%s</strong> is already associated with another Galaxy account, <strong>%s</strong>.  Please disassociate it from that account before attempting to associate it with a new account." % ( display_identifier, user_openid.user.email )
                if not trans.user.active and trans.app.config.user_activation_on:  # Account activation is ON and the user is INACTIVE.
                    if ( trans.app.config.activation_grace_period != 0 ):  # grace period is ON
                        if self.is_outside_grace_period( trans, trans.user.create_time ):  # User is outside the grace period. Login is disabled and he will have the activation email resent.
                            message, status = self.resend_verification_email( trans, trans.user.email, trans.user.username )
                        else:  # User is within the grace period, let him log in.
                            pass
                    else:  # Grace period is off. Login is disabled and user will have the activation email resent.
                        message, status = self.resend_verification_email( trans, trans.user.email, trans.user.username )
                elif not user_openid.user or user_openid.user == trans.user:
                    if openid_provider_obj.id:
                        user_openid.provider = openid_provider_obj.id
                    user_openid.session = trans.galaxy_session
                    if not openid_provider_obj.never_associate_with_user:
                        if not auto_associate and ( user_openid.user and user_openid.user.id == trans.user.id ):
                            message = "The OpenID <strong>%s</strong> is already associated with your Galaxy account, <strong>%s</strong>." % ( display_identifier, trans.user.email )
                            status = "warning"
                        else:
                            message = "The OpenID <strong>%s</strong> has been associated with your Galaxy account, <strong>%s</strong>." % ( display_identifier, trans.user.email )
                            status = "done"
                        user_openid.user = trans.user
                        trans.sa_session.add( user_openid )
                        trans.sa_session.flush()
                        trans.log_event( "User associated OpenID: %s" % display_identifier )
                    else:
                        message = "The OpenID <strong>%s</strong> cannot be used to log into your Galaxy account, but any post authentication actions have been performed." % ( openid_provider_obj.name )
                        status = "info"
                    openid_provider_obj.post_authentication( trans, trans.app.openid_manager, info )
                    if redirect:
                        message = '%s<br>Click <a href="%s"><strong>here</strong></a> to return to the page you were previously viewing.' % ( message, redirect )
                if redirect and status != "error":
                    return trans.response.send_redirect( redirect )
                return trans.response.send_redirect( url_for( controller='user',
                                                     action='openid_manage',
                                                     use_panels=True,
                                                     redirect=redirect,
                                                     message=message,
                                                     status=status ) )
            elif user_openid.user:
                trans.handle_user_login( user_openid.user )
                trans.log_event( "User logged in via OpenID: %s" % display_identifier )
                openid_provider_obj.post_authentication( trans, trans.app.openid_manager, info )
                if not redirect:
                    redirect = url_for( '/' )
                return trans.response.send_redirect( redirect )
            trans.sa_session.add( user_openid )
            trans.sa_session.flush()
            message = "OpenID authentication was successful, but you need to associate your OpenID with a Galaxy account."
            sreg_resp = trans.app.openid_manager.get_sreg( info )
            try:
                sreg_username_name = openid_provider_obj.use_for.get( 'username' )
                username = sreg_resp.get( sreg_username_name, '' )
            except AttributeError:
                username = ''
            try:
                sreg_email_name = openid_provider_obj.use_for.get( 'email' )
                email = sreg_resp.get( sreg_email_name, '' )
            except AttributeError:
                email = ''
            # OpenID success, but user not logged in, and not previously associated
            return trans.response.send_redirect( url_for( controller='user',
                                                 action='openid_associate',
                                                 use_panels=True,
                                                 redirect=redirect,
                                                 username=username,
                                                 email=email,
                                                 message=message,
                                                 status='warning' ) )
        elif info.status == trans.app.openid_manager.CANCEL:
            message = "Login via OpenID was cancelled by an action at the OpenID provider's site."
            status = "warning"
        elif info.status == trans.app.openid_manager.SETUP_NEEDED:
            if info.setup_url:
                return trans.response.send_redirect( info.setup_url )
            else:
                message = "Unable to log in via OpenID.  Setup at the provider is required before this OpenID can be used.  Please visit your provider's site to complete this step."
        return trans.response.send_redirect( url_for( controller='user',
                                                      action=action,
                                                      use_panels=True,
                                                      redirect=redirect,
                                                      message=message,
                                                      status=status ) )

    @web.expose
    def openid_associate( self, trans, cntrller='user', **kwd ):
        '''Associates a user with an OpenID log in'''
        if not trans.app.config.enable_openid:
            return trans.show_error_message( 'OpenID authentication is not enabled in this instance of Galaxy' )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        message = kwd.get( 'message', '' )
        status = kwd.get( 'status', 'done' )
        email = kwd.get( 'email', '' )
        username = kwd.get( 'username', '' )
        redirect = kwd.get( 'redirect', '' ).strip()
        params = util.Params( kwd )
        is_admin = cntrller == 'admin' and trans.user_is_admin()
        openids = trans.galaxy_session.openids
        user = None
        if not openids:
            return trans.show_error_message( 'You have not successfully completed an OpenID authentication in this session.  You can do so on the <a href="%s">login</a> page.' % url_for( controller='user', action='login', use_panels=use_panels ) )
        elif is_admin:
            return trans.show_error_message( 'Associating OpenIDs with accounts cannot be done by administrators.' )
        if kwd.get( 'login_button', False ):
            message, status, user, success = self.__validate_login( trans, **kwd )
            if success:
                openid_objs = []
                for openid in openids:
                    openid_provider_obj = trans.app.openid_providers.get( openid.provider )
                    if not openid_provider_obj or not openid_provider_obj.never_associate_with_user:
                        openid.user = user
                        trans.sa_session.add( openid )
                        trans.log_event( "User associated OpenID: %s" % openid.openid )
                    if openid_provider_obj and openid_provider_obj.has_post_authentication_actions():
                        openid_objs.append( openid_provider_obj )
                trans.sa_session.flush()
                if len( openid_objs ) == 1:
                    return trans.response.send_redirect( url_for( controller='user', action='openid_auth', openid_provider=openid_objs[0].id, redirect=redirect, auto_associate=True ) )
                elif openid_objs:
                    message = 'You have authenticated with several OpenID providers, please click the following links to execute the post authentication actions. '
                    message = "%s<br/><ul>" % ( message )
                    for openid in openid_objs:
                        message = '%s<li><a href="%s" target="_blank">%s</a></li>' % ( message, url_for( controller='user', action='openid_auth', openid_provider=openid.id, redirect=redirect, auto_associate=True ), openid.name )
                    message = "%s</ul>" % ( message )
                    return trans.response.send_redirect( url_for( controller='user',
                                                                  action='openid_manage',
                                                                  use_panels=use_panels,
                                                                  redirect=redirect,
                                                                  message=message,
                                                                  status='info' ) )
                if redirect:
                    return trans.response.send_redirect( redirect )
                return trans.response.send_redirect( url_for( controller='user',
                                                              action='openid_manage',
                                                              use_panels=use_panels,
                                                              redirect=redirect,
                                                              message=message,
                                                              status='info' ) )
        if kwd.get( 'create_user_button', False ):
            password = kwd.get( 'password', '' )
            confirm = kwd.get( 'confirm', '' )
            subscribe = params.get( 'subscribe', '' )
            subscribe_checked = CheckboxField.is_checked( subscribe )
            error = ''
            if not trans.app.config.allow_user_creation and not trans.user_is_admin():
                error = 'User registration is disabled.  Please contact your local Galaxy administrator for an account.'
            else:
                # Check email and password validity
                error = self.__validate( trans, params, email, password, confirm, username )
                if not error:
                    # all the values are valid
                    message, status, user, success = self.__register( trans,
                                                                      cntrller,
                                                                      subscribe_checked,
                                                                      **kwd )
                    if success:
                        openid_objs = []
                        for openid in openids:
                            openid_provider_obj = trans.app.openid_providers.get( openid.provider )
                            if not openid_provider_obj:
                                openid_provider_obj = trans.app.openid_providers.new_provider_from_identifier( openid.identifier )
                            if not openid_provider_obj.never_associate_with_user:
                                openid.user = user
                                trans.sa_session.add( openid )
                                trans.log_event( "User associated OpenID: %s" % openid.openid )
                            if openid_provider_obj.has_post_authentication_actions():
                                openid_objs.append( openid_provider_obj )
                        trans.sa_session.flush()
                        if len( openid_objs ) == 1:
                            return trans.response.send_redirect( url_for( controller='user', action='openid_auth', openid_provider=openid_objs[0].id, redirect=redirect, auto_associate=True ) )
                        elif openid_objs:
                            message = 'You have authenticated with several OpenID providers, please click the following links to execute the post authentication actions. '
                            message = "%s<br/><ul>" % ( message )
                            for openid in openid_objs:
                                message = '%s<li><a href="%s" target="_blank">%s</a></li>' % ( message, url_for( controller='user', action='openid_auth', openid_provider=openid.id, redirect=redirect, auto_associate=True ), openid.name )
                            message = "%s</ul>" % ( message )
                            return trans.response.send_redirect( url_for( controller='user',
                                                                          action='openid_manage',
                                                                          use_panels=True,
                                                                          redirect=redirect,
                                                                          message=message,
                                                                          status='info' ) )
                        if redirect:
                            return trans.response.send_redirect( redirect )
                        return trans.response.send_redirect( url_for( controller='user',
                                                                      action='openid_manage',
                                                                      use_panels=use_panels,
                                                                      redirect=redirect,
                                                                      message=message,
                                                                      status='info' ) )
                else:
                    message = error
                    status = 'error'
        if trans.webapp.name == 'galaxy':
            user_type_form_definition = self.__get_user_type_form_definition( trans, user=user, **kwd )
            user_type_fd_id = params.get( 'user_type_fd_id', 'none' )
            if user_type_fd_id == 'none' and user_type_form_definition is not None:
                user_type_fd_id = trans.security.encode_id( user_type_form_definition.id )
            user_type_fd_id_select_field = self.__build_user_type_fd_id_select_field( trans, selected_value=user_type_fd_id )
            widgets = self.__get_widgets( trans, user_type_form_definition, user=user, **kwd )
        else:
            user_type_fd_id_select_field = None
            user_type_form_definition = None
            widgets = []
        return trans.fill_template( '/user/openid_associate.mako',
                                    cntrller=cntrller,
                                    email=email,
                                    password='',
                                    confirm='',
                                    username=transform_publicname( trans, username ),
                                    header='',
                                    use_panels=use_panels,
                                    redirect=redirect,
                                    refresh_frames=[],
                                    message=message,
                                    status=status,
                                    active_view="user",
                                    subscribe_checked=False,
                                    user_type_fd_id_select_field=user_type_fd_id_select_field,
                                    user_type_form_definition=user_type_form_definition,
                                    widgets=widgets,
                                    openids=openids )

    @web.expose
    @web.require_login( 'manage OpenIDs' )
    def openid_disassociate( self, trans, **kwd ):
        '''Disassociates a user with an OpenID'''
        if not trans.app.config.enable_openid:
            return trans.show_error_message( 'OpenID authentication is not enabled in this instance of Galaxy' )
        params = util.Params( kwd )
        ids = params.get( 'id', None )
        message = params.get( 'message', None )
        status = params.get( 'status', None )
        use_panels = params.get( 'use_panels', False )
        user_openids = []
        if not ids:
            message = 'You must select at least one OpenID to disassociate from your Galaxy account.'
            status = 'error'
        else:
            ids = util.listify( params.id )
            for id in ids:
                id = trans.security.decode_id( id )
                user_openid = trans.sa_session.query( trans.app.model.UserOpenID ).get( int( id ) )
                if not user_openid or ( trans.user.id != user_openid.user_id ):
                    message = 'The selected OpenID(s) are not associated with your Galaxy account.'
                    status = 'error'
                    user_openids = []
                    break
                user_openids.append( user_openid )
            if user_openids:
                deleted_urls = []
                for user_openid in user_openids:
                    trans.sa_session.delete( user_openid )
                    deleted_urls.append( user_openid.openid )
                trans.sa_session.flush()
                for deleted_url in deleted_urls:
                    trans.log_event( "User disassociated OpenID: %s" % deleted_url )
                message = '%s OpenIDs were disassociated from your Galaxy account.' % len( ids )
                status = 'done'
        return trans.response.send_redirect( url_for( controller='user',
                                                      action='openid_manage',
                                                      use_panels=use_panels,
                                                      message=message,
                                                      status=status ) )

    @web.expose
    @web.require_login( 'manage OpenIDs' )
    def openid_manage( self, trans, **kwd ):
        '''Manage OpenIDs for user'''
        if not trans.app.config.enable_openid:
            return trans.show_error_message( 'OpenID authentication is not enabled in this instance of Galaxy' )
        use_panels = kwd.get( 'use_panels', False )
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "delete":
                return trans.response.send_redirect( url_for( controller='user',
                                                              action='openid_disassociate',
                                                              use_panels=use_panels,
                                                              id=kwd['id'] ) )
        kwd['redirect'] = kwd.get( 'redirect', url_for( controller='user', action='openid_manage', use_panels=True ) ).strip()
        kwd['openid_providers'] = trans.app.openid_providers
        return self.user_openid_grid( trans, **kwd )

    @web.expose
    def login( self, trans, refresh_frames=[], **kwd ):
        '''Handle Galaxy Log in'''
        redirect = kwd.get( 'redirect', trans.request.referer ).strip()
        root_url = url_for( '/', qualified=True )
        redirect_url = ''  # always start with redirect_url being empty
        # compare urls, to prevent a redirect from pointing (directly) outside of galaxy
        # or to enter a logout/login loop
        if not util.compare_urls( root_url, redirect, compare_path=False ) or util.compare_urls( url_for( controller='user', action='logout', qualified=True ), redirect ):
            redirect = root_url
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        message = kwd.get( 'message', '' )
        status = kwd.get( 'status', 'done' )
        header = ''
        user = trans.user
        email = kwd.get( 'email', '' )
        if user:
            # already logged in
            redirect_url = redirect
            message = 'You are already logged in.'
            status = 'info'
        elif kwd.get( 'login_button', False ):
            if trans.webapp.name == 'galaxy' and not refresh_frames:
                if trans.app.config.require_login:
                    refresh_frames = [ 'masthead', 'history', 'tools' ]
                else:
                    refresh_frames = [ 'masthead', 'history' ]
            message, status, user, success = self.__validate_login( trans, **kwd )
            if success:
                redirect_url = redirect
        if not user and trans.app.config.require_login:
            if trans.app.config.allow_user_creation:
                create_account_str = "  If you don't already have an account, <a href='%s'>you may create one</a>." % \
                    web.url_for( controller='user', action='create', cntrller='user' )
                if trans.webapp.name == 'galaxy':
                    header = require_login_template % ( "Galaxy instance", create_account_str )
                else:
                    header = require_login_template % ( "Galaxy tool shed", create_account_str )
            else:
                if trans.webapp.name == 'galaxy':
                    header = require_login_template % ( "Galaxy instance", "" )
                else:
                    header = require_login_template % ( "Galaxy tool shed", "" )
        return trans.fill_template( '/user/login.mako',
                                    email=email,
                                    header=header,
                                    use_panels=use_panels,
                                    redirect_url=redirect_url,
                                    redirect=redirect,
                                    refresh_frames=refresh_frames,
                                    message=message,
                                    status=status,
                                    openid_providers=trans.app.openid_providers,
                                    form_input_auto_focus=True,
                                    active_view="user" )

    def __validate_login( self, trans, **kwd ):
        """
        Function validates numerous cases that might happen during the login time.
        """
        message = kwd.get( 'message', '' )
        status = kwd.get( 'status', 'error' )
        email = kwd.get( 'email', '' )
        password = kwd.get( 'password', '' )
        username = kwd.get( 'username', '' )
        redirect = kwd.get( 'redirect', trans.request.referer ).strip()
        success = False
        user = trans.sa_session.query( trans.app.model.User ).filter( trans.app.model.User.table.c.email == email ).first()
        if not user:
            message = "No such user (please note that login is case sensitive)"
        elif user.deleted:
            message = "This account has been marked deleted, contact your local Galaxy administrator to restore the account."
            if trans.app.config.error_email_to is not None:
                message += ' Contact: %s' % trans.app.config.error_email_to
        elif user.external:
            message = "This account was created for use with an external authentication method, contact your local Galaxy administrator to activate it."
            if trans.app.config.error_email_to is not None:
                message += ' Contact: %s' % trans.app.config.error_email_to
        elif not user.check_password( password ):
            message = "Invalid password"
        elif trans.app.config.user_activation_on and not user.active:  # activation is ON and the user is INACTIVE
            if ( trans.app.config.activation_grace_period != 0 ):  # grace period is ON
                if self.is_outside_grace_period( trans, user.create_time ):  # User is outside the grace period. Login is disabled and he will have the activation email resent.
                    message, status = self.resend_verification_email( trans, email, username )
                else:  # User is within the grace period, let him log in.
                    message, success, status = self.proceed_login( trans, user, redirect )
            else:  # Grace period is off. Login is disabled and user will have the activation email resent.
                message, status = self.resend_verification_email( trans, email, username )
        else:  # activation is OFF
            message, success, status = self.proceed_login( trans, user, redirect )
        return ( message, status, user, success )

    def proceed_login( self, trans, user, redirect ):
        """
        Function processes user login. It is called in case all the login requirements are valid.
        """
        message = ''
        trans.handle_user_login( user )
        if trans.webapp.name == 'galaxy':
            trans.log_event( "User logged in" )
            message = 'You are now logged in as %s.<br>You can <a target="_top" href="%s">go back to the page you were visiting</a> or <a target="_top" href="%s">go to the home page</a>.' % \
                ( user.email, redirect, url_for( '/' ) )
            if trans.app.config.require_login:
                message += '  <a target="_top" href="%s">Click here</a> to continue to the home page.' % web.url_for( controller="root", action="welcome" )
        success = True
        status = 'done'
        return message, success, status

    @web.expose
    def resend_verification( self, trans ):
        """
        Exposed function for use outside of the class. E.g. when user click on the resend link in the masthead.
        """
        message, status = self.resend_verification_email( trans, None, None )
        if status == 'done':
            return trans.show_ok_message( message )
        else:
            return trans.show_error_message( message )

    def resend_verification_email( self, trans, email, username ):
        """
        Function resends the verification email in case user wants to log in with an inactive account or he clicks the resend link.
        """
        if email is None:  # User is coming from outside registration form, load email from trans
            email = trans.user.email
        if username is None:  # User is coming from outside registration form, load email from trans
            username = trans.user.username
        is_activation_sent = self.send_verification_email( trans, email, username)
        if is_activation_sent:
            message = 'This account has not been activated yet. The activation link has been sent again. Please check your email address <b>%s</b> including the spam/trash folder.<br><a target="_top" href="%s">Return to the home page</a>.' % ( email, url_for( '/' ) )
            status = 'error'
        else:
            message = 'This account has not been activated yet but we are unable to send the activation link. Please contact your local Galaxy administrator.<br><a target="_top" href="%s">Return to the home page</a>.' % url_for( '/' )
            status = 'error'
            if trans.app.config.error_email_to is not None:
                message += '<br>Error contact: %s' % trans.app.config.error_email_to
        return message, status

    def is_outside_grace_period( self, trans, create_time ):
        """
        Function checks whether the user is outside the config-defined grace period for inactive accounts.
        """
        #  Activation is forced and the user is not active yet. Check the grace period.
        activation_grace_period = trans.app.config.activation_grace_period
        #  Default value is 3 hours.
        if activation_grace_period is None:
            activation_grace_period = 3
        delta = timedelta( hours=int( activation_grace_period ) )
        time_difference = datetime.utcnow() - create_time
        return ( time_difference > delta or activation_grace_period == 0 )

    @web.expose
    def logout( self, trans, logout_all=False ):
        if trans.webapp.name == 'galaxy':
            if trans.app.config.require_login:
                refresh_frames = [ 'masthead', 'history', 'tools' ]
            else:
                refresh_frames = [ 'masthead', 'history' ]
            # Since logging an event requires a session, we'll log prior to ending the session
            trans.log_event( "User logged out" )
        else:
            refresh_frames = [ 'masthead' ]
        trans.handle_user_logout( logout_all=logout_all )
        message = 'You have been logged out.<br>You can log in again, <a target="_top" href="%s">go back to the page you were visiting</a> or <a target="_top" href="%s">go to the home page</a>.' % \
            ( trans.request.referer, url_for( '/' ) )
        if biostar.biostar_logged_in( trans ):
            biostar_url = biostar.biostar_logout( trans )
            if biostar_url:
                # TODO: It would be better if we automatically logged this user out of biostar
                message += '<br>To logout of Biostar, please click <a href="%s" target="_blank">here</a>.' % ( biostar_url )
        if trans.app.config.use_remote_user and trans.app.config.remote_user_logout_href:
            trans.response.send_redirect(trans.app.config.remote_user_logout_href)
        else:
            return trans.fill_template('/user/logout.mako',
                                       refresh_frames=refresh_frames,
                                       message=message,
                                       status='done',
                                       active_view="user" )

    @web.expose
    def create( self, trans, cntrller='user', redirect_url='', refresh_frames=[], **kwd ):
        params = util.Params( kwd )
        # If the honeypot field is not empty we are dealing with a bot.
        honeypot_field = params.get( 'bear_field', '' )
        if honeypot_field != '':
            return trans.show_error_message( "You've been flagged as a possible bot. If you are not, please try registering again and fill the form out carefully. <a target=\"_top\" href=\"%s\">Go to the home page</a>." ) % url_for( '/' )

        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', True ) )
        email = util.restore_text( params.get( 'email', '' ) )
        # Do not sanitize passwords, so take from kwd
        # instead of params ( which were sanitized )
        password = kwd.get( 'password', '' )
        confirm = kwd.get( 'confirm', '' )
        username = util.restore_text( params.get( 'username', '' ) )
        subscribe = params.get( 'subscribe', '' )
        subscribe_checked = CheckboxField.is_checked( subscribe )
        redirect = kwd.get( 'redirect', trans.request.referer ).strip()
        is_admin = cntrller == 'admin' and trans.user_is_admin
        if not trans.app.config.allow_user_creation and not trans.user_is_admin():
            message = 'User registration is disabled.  Please contact your local Galaxy administrator for an account.'
            if trans.app.config.error_email_to is not None:
                message += ' Contact: %s' % trans.app.config.error_email_to
            status = 'error'
        else:
            if not refresh_frames:
                if trans.webapp.name == 'galaxy':
                    if trans.app.config.require_login:
                        refresh_frames = [ 'masthead', 'history', 'tools' ]
                    else:
                        refresh_frames = [ 'masthead', 'history' ]
                else:
                    refresh_frames = [ 'masthead' ]
            # Create the user, save all the user info and login to Galaxy
            if params.get( 'create_user_button', False ):
                # Check email and password validity
                message = self.__validate( trans, params, email, password, confirm, username )
                if not message:
                    # All the values are valid
                    message, status, user, success = self.__register( trans,
                                                                      cntrller,
                                                                      subscribe_checked,
                                                                      **kwd )
                    if trans.webapp.name == 'tool_shed':
                        redirect_url = url_for( '/' )
                    if success and not is_admin:
                        # The handle_user_login() method has a call to the history_set_default_permissions() method
                        # (needed when logging in with a history), user needs to have default permissions set before logging in
                        trans.handle_user_login( user )
                        trans.log_event( "User created a new account" )
                        trans.log_event( "User logged in" )
                    if success and is_admin:
                        message = 'Created new user account (%s)' % user.email
                        trans.response.send_redirect( web.url_for( controller='admin',
                                                                   action='users',
                                                                   cntrller=cntrller,
                                                                   message=message,
                                                                   status=status ) )
                else:
                    status = 'error'
        if trans.webapp.name == 'galaxy':
            user_type_form_definition = self.__get_user_type_form_definition( trans, user=None, **kwd )
            user_type_fd_id = params.get( 'user_type_fd_id', 'none' )
            if user_type_fd_id == 'none' and user_type_form_definition is not None:
                user_type_fd_id = trans.security.encode_id( user_type_form_definition.id )
            user_type_fd_id_select_field = self.__build_user_type_fd_id_select_field( trans, selected_value=user_type_fd_id )
            widgets = self.__get_widgets( trans, user_type_form_definition, user=None, **kwd )
            #  Warning message that is shown on the registration page.
            registration_warning_message = trans.app.config.registration_warning_message
        else:
            user_type_fd_id_select_field = None
            user_type_form_definition = None
            widgets = []
            registration_warning_message = None
        return trans.fill_template( '/user/register.mako',
                                    cntrller=cntrller,
                                    email=email,
                                    username=transform_publicname( trans, username ),
                                    subscribe_checked=subscribe_checked,
                                    user_type_fd_id_select_field=user_type_fd_id_select_field,
                                    user_type_form_definition=user_type_form_definition,
                                    widgets=widgets,
                                    use_panels=use_panels,
                                    redirect=redirect,
                                    redirect_url=redirect_url,
                                    refresh_frames=refresh_frames,
                                    registration_warning_message=registration_warning_message,
                                    message=message,
                                    status=status )

    def __register( self, trans, cntrller, subscribe_checked, **kwd ):
        email = util.restore_text( kwd.get( 'email', '' ) )
        password = kwd.get( 'password', '' )
        username = util.restore_text( kwd.get( 'username', '' ) )
        message = kwd.get( 'message', '' )
        status = kwd.get( 'status', 'done' )
        is_admin = cntrller == 'admin' and trans.user_is_admin()
        user = self.create_user( trans=trans, email=email, username=username, password=password )
        error = ''
        success = True
        if trans.webapp.name == 'galaxy':
            # Save other information associated with the user, if any
            user_info_forms = self.get_all_forms( trans,
                                                  filter=dict( deleted=False ),
                                                  form_type=trans.app.model.FormDefinition.types.USER_INFO )
            # If there are no user forms available then there is nothing to save
            if user_info_forms:
                user_type_fd_id = kwd.get( 'user_type_fd_id', 'none' )
                if user_type_fd_id not in [ 'none' ]:
                    user_type_form_definition = trans.sa_session.query( trans.app.model.FormDefinition ).get( trans.security.decode_id( user_type_fd_id ) )
                    values = self.get_form_values( trans, user, user_type_form_definition, **kwd )
                    form_values = trans.app.model.FormValues( user_type_form_definition, values )
                    trans.sa_session.add( form_values )
                    trans.sa_session.flush()
                    user.values = form_values
                    trans.sa_session.add( user )
                    trans.sa_session.flush()
            if subscribe_checked:
                # subscribe user to email list
                if trans.app.config.smtp_server is None:
                    error = "Now logged in as " + user.email + ". However, subscribing to the mailing list has failed because mail is not configured for this Galaxy instance. <br>Please contact your local Galaxy administrator."
                else:
                    body = 'Join Mailing list.\n'
                    to = trans.app.config.mailing_join_addr
                    frm = email
                    subject = 'Join Mailing List'
                    try:
                        util.send_mail( frm, to, subject, body, trans.app.config )
                    except:
                        error = "Now logged in as " + user.email + ". However, subscribing to the mailing list has failed."
            if not error and not is_admin:
                # The handle_user_login() method has a call to the history_set_default_permissions() method
                # (needed when logging in with a history), user needs to have default permissions set before logging in
                trans.handle_user_login( user )
                trans.log_event( "User created a new account" )
                trans.log_event( "User logged in" )
            elif not error:
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='users',
                                                           message='Created new user account (%s)' % user.email,
                                                           status=status ) )
        if error:
            message = error
            status = 'error'
            success = False
        else:
            if trans.webapp.name == 'galaxy' and trans.app.config.user_activation_on:
                is_activation_sent = self.send_verification_email( trans, email, username )
                if is_activation_sent:
                    message = 'Now logged in as %s.<br>Verification email has been sent to your email address. Please verify it by clicking the activation link in the email.<br>Please check your spam/trash folder in case you cannot find the message.<br><a target="_top" href="%s">Return to the home page.</a>' % ( user.email, url_for( '/' ) )
                    success = True
                else:
                    message = 'Unable to send activation email, please contact your local Galaxy administrator.'
                    if trans.app.config.error_email_to is not None:
                        message += ' Contact: %s' % trans.app.config.error_email_to
                    success = False
            else:  # User activation is OFF, proceed without sending the activation email.
                message = 'Now logged in as %s.<br><a target="_top" href="%s">Return to the home page.</a>' % ( user.email, url_for( '/' ) )
                success = True
        return ( message, status, user, success )

    def send_verification_email( self, trans, email, username ):
        """
        Send the verification email containing the activation link to the user's email.
        """
        if username is None:
            username = trans.user.username
        activation_link = self.prepare_activation_link( trans, email )

        body = ("Hello %s,\n\n"
                "In order to complete the activation process for %s begun on %s at %s, please click on the following link to verify your account:\n\n"
                "%s \n\n"
                "By clicking on the above link and opening a Galaxy account you are also confirming that you have read and agreed to Galaxy's Terms and Conditions for use of this service (%s). This includes a quota limit of one account per user. Attempts to subvert this limit by creating multiple accounts or through any other method may result in termination of all associated accounts and data.\n\n"
                "Please contact us if you need help with your account at: %s. You can also browse resources available at: %s. \n\n"
                "More about the Galaxy Project can be found at galaxyproject.org\n\n"
                "Your Galaxy Team" % (username, email,
                                      datetime.utcnow().strftime( "%D"),
                                      trans.request.host, activation_link,
                                      trans.app.config.terms_url,
                                      trans.app.config.error_email_to,
                                      trans.app.config.instance_resource_url))
        to = email
        frm = trans.app.config.activation_email
        subject = 'Galaxy Account Activation'
        try:
            util.send_mail( frm, to, subject, body, trans.app.config )
            return True
        except:
            return False

    def prepare_activation_link( self, trans, email ):
        """
        Prepares the account activation link for the user.
        """
        activation_token = self.get_activation_token( trans, email )
        activation_link = url_for( controller='user', action='activate', activation_token=activation_token, email=email, qualified=True  )
        return activation_link

    def get_activation_token( self, trans, email ):
        """
        Checks for the activation token. Creates new activation token and stores it in the database if none found.
        """
        user = trans.sa_session.query( trans.app.model.User ).filter( trans.app.model.User.table.c.email == email ).first()
        activation_token = user.activation_token
        if activation_token is None:
            activation_token = hash_util.new_secure_hash( str( random.getrandbits( 256 ) ) )
            user.activation_token = activation_token
            trans.sa_session.add( user )
            trans.sa_session.flush()
        return activation_token

    @web.expose
    def activate( self, trans, **kwd ):
        """
        Function checks whether token fits the user and then activates the user's account.
        """
        params = util.Params( kwd, sanitize=False )
        email = urllib.unquote( params.get( 'email', None ) )
        activation_token = params.get( 'activation_token', None )

        if email is None or activation_token is None:
            #  We don't have the email or activation_token, show error.
            return trans.show_error_message( "You are using wrong activation link. Try to log-in and we will send you a new activation email. <br><a href='%s'>Go to login page.</a>" ) % web.url_for( controller="root", action="index" )
        else:
            # Find the user
            user = trans.sa_session.query( trans.app.model.User ).filter( trans.app.model.User.table.c.email == email ).first()
            # If the user is active already don't try to activate
            if user.active is True:
                return trans.show_ok_message( "Your account is already active. Nothing has changed. <br><a href='%s'>Go to login page.</a>" ) % web.url_for( controller='root', action='index' )
            if user.activation_token == activation_token:
                user.activation_token = None
                user.active = True
                trans.sa_session.add(user)
                trans.sa_session.flush()
                return trans.show_ok_message( "Your account has been successfully activated! <br><a href='%s'>Go to login page.</a>" ) % web.url_for( controller='root', action='index' )
            else:
                #  Tokens don't match. Activation is denied.
                return trans.show_error_message( "You are using wrong activation link. Try to log in and we will send you a new activation email. <br><a href='%s'>Go to login page.</a>" ) % web.url_for( controller='root', action='index' )
        return

    def __get_user_type_form_definition( self, trans, user=None, **kwd ):
        params = util.Params( kwd )
        if user and user.values:
            user_type_fd_id = trans.security.encode_id( user.values.form_definition.id )
        else:
            user_type_fd_id = params.get( 'user_type_fd_id', 'none' )
        if user_type_fd_id not in [ 'none' ]:
            user_type_form_definition = trans.sa_session.query( trans.app.model.FormDefinition ).get( trans.security.decode_id( user_type_fd_id ) )
        else:
            user_type_form_definition = None
        return user_type_form_definition

    def __get_widgets( self, trans, user_type_form_definition, user=None, **kwd ):
        widgets = []
        if user_type_form_definition:
            if user:
                if user.values:
                    widgets = user_type_form_definition.get_widgets( user=user,
                                                                     contents=user.values.content,
                                                                     **kwd )
                else:
                    widgets = user_type_form_definition.get_widgets( None, contents={}, **kwd )
            else:
                widgets = user_type_form_definition.get_widgets( None, contents={}, **kwd )
        return widgets

    @web.expose
    def manage_user_info( self, trans, cntrller, **kwd ):
        '''Manage a user's login, password, public username, type, addresses, etc.'''
        params = util.Params( kwd )
        user_id = params.get( 'id', None )
        if user_id:
            user = trans.sa_session.query( trans.app.model.User ).get( trans.security.decode_id( user_id ) )
        else:
            user = trans.user
        if not user:
            raise AssertionError("The user id (%s) is not valid" % str( user_id ))
        email = util.restore_text( params.get( 'email', user.email ) )
        username = util.restore_text( params.get( 'username', '' ) )
        if not username:
            username = user.username
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        if trans.webapp.name == 'galaxy':
            user_type_form_definition = self.__get_user_type_form_definition( trans, user=user, **kwd )
            user_type_fd_id = params.get( 'user_type_fd_id', 'none' )
            if user_type_fd_id == 'none' and user_type_form_definition is not None:
                user_type_fd_id = trans.security.encode_id( user_type_form_definition.id )
            user_type_fd_id_select_field = self.__build_user_type_fd_id_select_field( trans, selected_value=user_type_fd_id )
            widgets = self.__get_widgets( trans, user_type_form_definition, user=user, **kwd )
            # user's addresses
            show_filter = util.restore_text( params.get( 'show_filter', 'Active'  ) )
            if show_filter == 'All':
                addresses = [address for address in user.addresses]
            elif show_filter == 'Deleted':
                addresses = [address for address in user.addresses if address.deleted]
            else:
                addresses = [address for address in user.addresses if not address.deleted]
            user_info_forms = self.get_all_forms( trans,
                                                  filter=dict( deleted=False ),
                                                  form_type=trans.app.model.FormDefinition.types.USER_INFO )
            return trans.fill_template( '/webapps/galaxy/user/manage_info.mako',
                                        cntrller=cntrller,
                                        user=user,
                                        email=email,
                                        username=username,
                                        user_type_fd_id_select_field=user_type_fd_id_select_field,
                                        user_info_forms=user_info_forms,
                                        user_type_form_definition=user_type_form_definition,
                                        user_type_fd_id=user_type_fd_id,
                                        widgets=widgets,
                                        addresses=addresses,
                                        show_filter=show_filter,
                                        message=message,
                                        status=status )
        else:
            return trans.fill_template( '/webapps/tool_shed/user/manage_info.mako',
                                        cntrller=cntrller,
                                        user=user,
                                        email=email,
                                        username=username,
                                        message=message,
                                        status=status )

    # For REMOTE_USER, we need the ability to just edit the username
    @web.expose
    @web.require_login( "to manage the public name" )
    def edit_username( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        is_admin = cntrller == 'admin' and trans.user_is_admin()
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        user_id = params.get( 'user_id', None )
        if user_id and is_admin:
            user = trans.sa_session.query( trans.app.model.User ).get( trans.security.decode_id( user_id ) )
        else:
            user = trans.user
        if user and params.get( 'change_username_button', False ):
            username = kwd.get( 'username', '' )
            if username:
                message = validate_publicname( trans, username, user )
            if message:
                status = 'error'
            else:
                user.username = username
                trans.sa_session.add( user )
                trans.sa_session.flush()
                message = 'The username has been updated with the changes.'
        return trans.fill_template( '/user/username.mako',
                                    cntrller=cntrller,
                                    user=user,
                                    username=user.username,
                                    message=message,
                                    status=status )

    @web.expose
    def edit_info( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        is_admin = cntrller == 'admin' and trans.user_is_admin()
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        user_id = params.get( 'user_id', None )
        if user_id and is_admin:
            user = trans.sa_session.query( trans.app.model.User ).get( trans.security.decode_id( user_id ) )
        elif user_id and ( not trans.user or trans.user.id != trans.security.decode_id( user_id ) ):
            message = 'Invalid user id'
            status = 'error'
            user = None
        else:
            user = trans.user
        if user and params.get( 'login_info_button', False ):
            # Editing email and username
            email = util.restore_text( params.get( 'email', '' ) )
            username = util.restore_text( params.get( 'username', '' ) ).lower()
            # Validate the new values for email and username
            message = validate_email( trans, email, user )
            if not message and username:
                message = validate_publicname( trans, username, user )
            if message:
                status = 'error'
            else:
                # The user's private role name must match the user's login ( email )
                private_role = trans.app.security_agent.get_private_user_role( user )
                private_role.name = email
                private_role.description = 'Private role for ' + email
                # Now change the user info
                user.email = email
                user.username = username
                trans.sa_session.add_all( ( user, private_role ) )
                trans.sa_session.flush()
                message = 'The login information has been updated with the changes.'
        elif user and params.get( 'change_password_button', False ):
            # Editing password.  Do not sanitize passwords, so get from kwd
            # and not params (which were sanitized).
            password = kwd.get( 'password', '' )
            confirm = kwd.get( 'confirm', '' )
            ok = True
            if not is_admin:
                # If the current user is changing their own password, validate their current password
                current = kwd.get( 'current', '' )
                if not trans.user.check_password( current ):
                    message = 'Invalid current password'
                    status = 'error'
                    ok = False
            if ok:
                # Validate the new password
                message = validate_password( trans, password, confirm )
                if message:
                    status = 'error'
                else:
                    # Save new password
                    user.set_password_cleartext( password )
                    # Invalidate all other sessions
                    for other_galaxy_session in trans.sa_session.query( trans.app.model.GalaxySession ) \
                                                     .filter( and_( trans.app.model.GalaxySession.table.c.user_id == trans.user.id,
                                                                    trans.app.model.GalaxySession.table.c.is_valid is True,
                                                                    trans.app.model.GalaxySession.table.c.id != trans.galaxy_session.id ) ):
                        other_galaxy_session.is_valid = False
                        trans.sa_session.add( other_galaxy_session )
                    trans.sa_session.add( user )
                    trans.sa_session.flush()
                    trans.log_event( "User change password" )
                    message = 'The password has been changed and any other existing Galaxy sessions have been logged out (but jobs in histories in those sessions will not be interrupted).'
        elif user and params.get( 'edit_user_info_button', False ):
            # Edit user information - webapp MUST BE 'galaxy'
            user_type_fd_id = params.get( 'user_type_fd_id', 'none' )
            if user_type_fd_id not in [ 'none' ]:
                user_type_form_definition = trans.sa_session.query( trans.app.model.FormDefinition ).get( trans.security.decode_id( user_type_fd_id ) )
            elif user.values:
                user_type_form_definition = user.values.form_definition
            else:
                # User was created before any of the user_info forms were created
                user_type_form_definition = None
            if user_type_form_definition:
                values = self.get_form_values( trans, user, user_type_form_definition, **kwd )
            else:
                values = {}
            flush_needed = False
            if user.values:
                # Editing the user info of an existing user with existing user info
                user.values.content = values
                trans.sa_session.add( user.values )
                flush_needed = True
            elif values:
                form_values = trans.model.FormValues( user_type_form_definition, values )
                trans.sa_session.add( form_values )
                user.values = form_values
                flush_needed = True
            if flush_needed:
                trans.sa_session.add( user )
                trans.sa_session.flush()
            message = "The user information has been updated with the changes."
        if user and trans.webapp.name == 'galaxy' and is_admin:
            kwd[ 'user_id' ] = trans.security.encode_id( user.id )
        kwd[ 'id' ] = user_id
        if message:
            kwd[ 'message' ] = util.sanitize_text( message )
        if status:
            kwd[ 'status' ] = status
        return trans.response.send_redirect( web.url_for( controller='user',
                                                          action='manage_user_info',
                                                          cntrller=cntrller,
                                                          **kwd ) )

    @web.expose
    def reset_password( self, trans, email=None, **kwd ):
        if trans.app.config.smtp_server is None:
            return trans.show_error_message( "Mail is not configured for this Galaxy instance.  Please contact your local Galaxy administrator." )
        message = util.sanitize_text(util.restore_text( kwd.get( 'message', '' ) ))
        status = 'done'
        if kwd.get( 'reset_password_button', False ):
            reset_user = trans.sa_session.query( trans.app.model.User ).filter( trans.app.model.User.table.c.email == email ).first()
            user = trans.get_user()
            if reset_user:
                if user and user.id != reset_user.id:
                    message = "You may only reset your own password"
                    status = 'error'
                else:
                    chars = string.letters + string.digits
                    new_pass = ""
                    reset_password_length = getattr( trans.app.config, "reset_password_length", 15 )
                    for i in range(reset_password_length):
                        new_pass = new_pass + random.choice(chars)
                    host = trans.request.host.split(':')[0]
                    if host == 'localhost':
                        host = socket.getfqdn()
                    body = 'Your password on %s has been reset to:\n\n  %s\n' % ( host, new_pass )
                    to = email
                    frm = 'galaxy-no-reply@' + host
                    subject = 'Galaxy Password Reset'
                    try:
                        util.send_mail( frm, to, subject, body, trans.app.config )
                        reset_user.set_password_cleartext( new_pass )
                        trans.sa_session.add( reset_user )
                        trans.sa_session.flush()
                        trans.log_event( "User reset password: %s" % email )
                        message = "Password has been reset and emailed to: %s.  <a href='%s'>Click here</a> to return to the login form." % ( email, web.url_for( controller='user', action='login' ) )
                    except Exception, e:
                        message = 'Failed to reset password: %s' % str( e )
                        status = 'error'
                    return trans.response.send_redirect( web.url_for( controller='user',
                                                                      action='reset_password',
                                                                      message=message,
                                                                      status=status ) )
            elif email is not None:
                message = "The specified user does not exist"
                status = 'error'
            elif email is None:
                email = ""
        return trans.fill_template( '/user/reset_password.mako',
                                    message=message,
                                    status=status )

    def __validate( self, trans, params, email, password, confirm, username ):
        # If coming from the tool shed webapp, we'll require a public user name
        if trans.webapp.name == 'tool_shed':
            if not username:
                return "A public user name is required in the tool shed."
            if username in [ 'repos' ]:
                return "The term <b>%s</b> is a reserved word in the tool shed, so it cannot be used as a public user name." % username
        message = "\n".join( [ validate_email( trans, email ),
                               validate_password( trans, password, confirm ),
                               validate_publicname( trans, username ) ] ).rstrip()
        if not message:
            if trans.webapp.name == 'galaxy':
                if self.get_all_forms( trans,
                                       filter=dict( deleted=False ),
                                       form_type=trans.app.model.FormDefinition.types.USER_INFO ):
                    user_type_fd_id = params.get( 'user_type_fd_id', 'none' )
                    if user_type_fd_id in [ 'none' ]:
                        return "Select the user's type and information"
        return message

    @web.expose
    def set_default_permissions( self, trans, cntrller, **kwd ):
        """Sets the user's default permissions for the new histories"""
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        if trans.user:
            if 'update_roles_button' in kwd:
                p = util.Params( kwd )
                permissions = {}
                for k, v in trans.app.model.Dataset.permitted_actions.items():
                    in_roles = p.get( k + '_in', [] )
                    if not isinstance( in_roles, list ):
                        in_roles = [ in_roles ]
                    in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in in_roles ]
                    action = trans.app.security_agent.get_action( v.action ).action
                    permissions[ action ] = in_roles
                trans.app.security_agent.user_set_default_permissions( trans.user, permissions )
                message = 'Default new history permissions have been changed.'
            return trans.fill_template( 'user/permissions.mako',
                                        cntrller=cntrller,
                                        message=message,
                                        status=status )
        else:
            # User not logged in, history group must be only public
            return trans.show_error_message( "You must be logged in to change your default permitted actions." )

    @web.expose
    @web.require_login()
    def toolbox_filters( self, trans, cntrller, **kwd ):
        """
            Sets the user's default filters for the toolbox.
            Toolbox filters are specified in galaxy.ini.
            The user can activate them and the choice is stored in user_preferences.
        """

        def get_filter_mapping( db_filters, config_filters ):
            """
                Compare the allowed filters from the galaxy.ini config file with the previously saved or default filters from the database.
                We need that to toogle the checkboxes for the formular in the right way.
                Furthermore we extract all information associated to a filter to display them in the formular.
            """
            filters = list()
            for filter_name in config_filters:
                if ":" in filter_name:
                    # Should be a submodule of filters (e.g. examples:restrict_development_tools)
                    (module_name, function_name) = filter_name.rsplit(":", 1)
                    module_name = 'galaxy.tools.filters.%s' % module_name.strip()
                    module = __import__( module_name, globals(), fromlist=['temp_module'] )
                    function = getattr( module, function_name.strip() )
                else:
                    # No module found it has to be explicitly imported.
                    module = __import__( 'galaxy.tools.filters', globals(), fromlist=['temp_module'] )
                    function = getattr( globals(), filter_name.strip() )

                doc_string = docstring_trim( function.__doc__ )
                split = doc_string.split('\n\n')
                if split:
                    sdesc = split[0]
                else:
                    log.error( 'No description specified in the __doc__ string for %s.' % filter_name )
                if len(split) > 1:
                    description = split[1]
                else:
                    description = ''

                if filter_name in db_filters:
                    filters.append( dict( filterpath=filter_name, short_desc=sdesc, desc=description, checked=True ) )
                else:
                    filters.append( dict( filterpath=filter_name, short_desc=sdesc, desc=description, checked=False ) )
            return filters

        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )

        user_id = params.get( 'user_id', False )
        if user_id:
            user = trans.sa_session.query( trans.app.model.User ).get( trans.security.decode_id( user_id ) )
        else:
            user = trans.user

        if user:
            saved_user_tool_filters = list()
            saved_user_section_filters = list()
            saved_user_label_filters = list()

            for name, value in user.preferences.items():
                if name == 'toolbox_tool_filters':
                    saved_user_tool_filters = listify( value, do_strip=True )
                elif name == 'toolbox_section_filters':
                    saved_user_section_filters = listify( value, do_strip=True )
                elif name == 'toolbox_label_filters':
                    saved_user_label_filters = listify( value, do_strip=True )

            tool_filters = get_filter_mapping( saved_user_tool_filters, trans.app.config.user_tool_filters )
            section_filters = get_filter_mapping( saved_user_section_filters, trans.app.config.user_section_filters )
            label_filters = get_filter_mapping( saved_user_label_filters, trans.app.config.user_label_filters )

            return trans.fill_template( 'user/toolbox_filters.mako',
                                        cntrller=cntrller,
                                        message=message,
                                        tool_filters=tool_filters,
                                        section_filters=section_filters,
                                        label_filters=label_filters,
                                        user=user,
                                        status=status )
        else:
            # User not logged in, history group must be only public
            return trans.show_error_message( "You must be logged in to change private toolbox filters." )

    @web.expose
    @web.require_login( "to change the private toolbox filters" )
    def edit_toolbox_filters( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', '' ) )
        user_id = params.get( 'user_id', False )
        if not user_id:
            # User must be logged in to create a new address
            return trans.show_error_message( "You must be logged in to change the ToolBox filters." )

        user = trans.sa_session.query( trans.app.model.User ).get( trans.security.decode_id( user_id ) )

        if params.get( 'edit_toolbox_filter_button', False ):
            tool_filters = list()
            section_filters = list()
            label_filters = list()
            for name, state in params.flatten():
                if state == 'on':
                    if name.startswith('t_'):
                        tool_filters.append( name[2:] )
                    elif name.startswith('l_'):
                        label_filters.append( name[2:] )
                    elif name.startswith('s_'):
                        section_filters.append( name[2:] )
            user.preferences['toolbox_tool_filters'] = ','.join( tool_filters )
            user.preferences['toolbox_section_filters'] = ','.join( section_filters )
            user.preferences['toolbox_label_filters'] = ','.join( label_filters )

            trans.sa_session.add( user )
            trans.sa_session.flush()
            message = 'ToolBox filters has been updated.'
            kwd = dict( message=message, status='done' )

        # Display the ToolBox filters form with the current values filled in
        return self.toolbox_filters( trans, cntrller, **kwd )

    @web.expose
    @web.require_login( "to get most recently used tool" )
    @web.json_pretty
    def get_most_recently_used_tool_async( self, trans ):
        """ Returns information about the most recently used tool. """

        # Get most recently used tool.
        query = trans.sa_session.query( self.app.model.Job.tool_id ).join( self.app.model.History ) \
                                .filter( self.app.model.History.user == trans.user ) \
                                .order_by( self.app.model.Job.create_time.desc() ).limit(1)
        tool_id = query[0][0]  # Get first element in first row of query.
        tool = self.get_toolbox().get_tool( tool_id )

        # Return tool info.
        tool_info = {"id": tool.id,
                     "link": url_for( controller='tool_runner', tool_id=tool.id ),
                     "target": tool.target,
                     "name": tool.name,  # TODO: translate this using _()
                     "minsizehint": tool.uihints.get( 'minwidth', -1 ),
                     "description": tool.description}
        return tool_info

    @web.expose
    def manage_addresses(self, trans, **kwd):
        if trans.user:
            params = util.Params( kwd )
            message = util.restore_text( params.get( 'message', '' ) )
            status = params.get( 'status', 'done' )
            show_filter = util.restore_text( params.get( 'show_filter', 'Active' ) )
            if show_filter == 'All':
                addresses = [address for address in trans.user.addresses]
            elif show_filter == 'Deleted':
                addresses = [address for address in trans.user.addresses if address.deleted]
            else:
                addresses = [address for address in trans.user.addresses if not address.deleted]
            return trans.fill_template( 'user/address.mako',
                                        addresses=addresses,
                                        show_filter=show_filter,
                                        message=message,
                                        status=status)
        else:
            # User not logged in, history group must be only public
            return trans.show_error_message( "You must be logged in to change your default permitted actions." )

    @web.expose
    def new_address( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        is_admin = cntrller == 'admin' and trans.user_is_admin()
        user_id = params.get( 'user_id', False )
        if not user_id:
            # User must be logged in to create a new address
            return trans.show_error_message( "You must be logged in to create a new address." )
        user = trans.sa_session.query( trans.app.model.User ).get( trans.security.decode_id( user_id ) )
        short_desc = util.restore_text( params.get( 'short_desc', ''  ) )
        name = util.restore_text( params.get( 'name', ''  ) )
        institution = util.restore_text( params.get( 'institution', ''  ) )
        address = util.restore_text( params.get( 'address', ''  ) )
        city = util.restore_text( params.get( 'city', ''  ) )
        state = util.restore_text( params.get( 'state', ''  ) )
        postal_code = util.restore_text( params.get( 'postal_code', ''  ) )
        country = util.restore_text( params.get( 'country', ''  ) )
        phone = util.restore_text( params.get( 'phone', ''  ) )
        ok = True
        if not trans.app.config.allow_user_creation and not is_admin:
            return trans.show_error_message( 'User registration is disabled.  Please contact your local Galaxy administrator for an account.' )
        if params.get( 'new_address_button', False ):
            if not short_desc:
                ok = False
                message = 'Enter a short description for this address'
            elif not name:
                ok = False
                message = 'Enter the name'
            elif not institution:
                ok = False
                message = 'Enter the institution associated with the user'
            elif not address:
                ok = False
                message = 'Enter the address'
            elif not city:
                ok = False
                message = 'Enter the city'
            elif not state:
                ok = False
                message = 'Enter the state/province/region'
            elif not postal_code:
                ok = False
                message = 'Enter the postal code'
            elif not country:
                ok = False
                message = 'Enter the country'
            if ok:
                user_address = trans.model.UserAddress( user=user,
                                                        desc=short_desc,
                                                        name=name,
                                                        institution=institution,
                                                        address=address,
                                                        city=city,
                                                        state=state,
                                                        postal_code=postal_code,
                                                        country=country,
                                                        phone=phone )
                trans.sa_session.add( user_address )
                trans.sa_session.flush()
                message = 'Address (%s) has been added' % user_address.desc
                new_kwd = dict( message=message, status=status )
                if is_admin:
                    new_kwd[ 'user_id' ] = trans.security.encode_id( user.id )
                return trans.response.send_redirect( web.url_for( controller='user',
                                                                  action='manage_user_info',
                                                                  cntrller=cntrller,
                                                                  **new_kwd ) )
        # Display the address form with the current values filled in
        return trans.fill_template( 'user/new_address.mako',
                                    cntrller=cntrller,
                                    user=user,
                                    short_desc=short_desc,
                                    name=name,
                                    institution=institution,
                                    address=address,
                                    city=city,
                                    state=state,
                                    postal_code=postal_code,
                                    country=country,
                                    phone=phone,
                                    message=message,
                                    status=status )

    @web.expose
    def edit_address( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        is_admin = cntrller == 'admin' and trans.user_is_admin()
        user_id = params.get( 'user_id', False )
        if not user_id:
            # User must be logged in to create a new address
            return trans.show_error_message( "You must be logged in to create a new address." )
        user = trans.sa_session.query( trans.app.model.User ).get( trans.security.decode_id( user_id ) )
        address_id = params.get( 'address_id', None )
        if not address_id:
            return trans.show_error_message( "No address id received for editing." )
        address_obj = trans.sa_session.query( trans.app.model.UserAddress ).get( trans.security.decode_id( address_id ) )
        if params.get( 'edit_address_button', False  ):
            short_desc = util.restore_text( params.get( 'short_desc', ''  ) )
            name = util.restore_text( params.get( 'name', ''  ) )
            institution = util.restore_text( params.get( 'institution', ''  ) )
            address = util.restore_text( params.get( 'address', ''  ) )
            city = util.restore_text( params.get( 'city', ''  ) )
            state = util.restore_text( params.get( 'state', ''  ) )
            postal_code = util.restore_text( params.get( 'postal_code', ''  ) )
            country = util.restore_text( params.get( 'country', ''  ) )
            phone = util.restore_text( params.get( 'phone', ''  ) )
            ok = True
            if not short_desc:
                ok = False
                message = 'Enter a short description for this address'
            elif not name:
                ok = False
                message = 'Enter the name'
            elif not institution:
                ok = False
                message = 'Enter the institution associated with the user'
            elif not address:
                ok = False
                message = 'Enter the address'
            elif not city:
                ok = False
                message = 'Enter the city'
            elif not state:
                ok = False
                message = 'Enter the state/province/region'
            elif not postal_code:
                ok = False
                message = 'Enter the postal code'
            elif not country:
                ok = False
                message = 'Enter the country'
            if ok:
                address_obj.desc = short_desc
                address_obj.name = name
                address_obj.institution = institution
                address_obj.address = address
                address_obj.city = city
                address_obj.state = state
                address_obj.postal_code = postal_code
                address_obj.country = country
                address_obj.phone = phone
                trans.sa_session.add( address_obj )
                trans.sa_session.flush()
                message = 'Address (%s) has been updated.' % address_obj.desc
                new_kwd = dict( message=message, status=status )
                if is_admin:
                    new_kwd[ 'user_id' ] = trans.security.encode_id( user.id )
                return trans.response.send_redirect( web.url_for( controller='user',
                                                                  action='manage_user_info',
                                                                  cntrller=cntrller,
                                                                  **new_kwd ) )
        # Display the address form with the current values filled in
        return trans.fill_template( 'user/edit_address.mako',
                                    cntrller=cntrller,
                                    user=user,
                                    address_obj=address_obj,
                                    message=message,
                                    status=status )

    @web.expose
    def delete_address( self, trans, cntrller, address_id=None, user_id=None ):
        try:
            user_address = trans.sa_session.query( trans.app.model.UserAddress ).get( trans.security.decode_id( address_id ) )
        except:
            message = 'Invalid address is (%s)' % address_id
            status = 'error'
        if user_address:
            user_address.deleted = True
            trans.sa_session.add( user_address )
            trans.sa_session.flush()
            message = 'Address (%s) deleted' % user_address.desc
            status = 'done'
        return trans.response.send_redirect( web.url_for( controller='user',
                                                          action='manage_user_info',
                                                          cntrller=cntrller,
                                                          user_id=user_id,
                                                          message=message,
                                                          status=status ) )

    @web.expose
    def undelete_address( self, trans, cntrller, address_id=None, user_id=None ):
        try:
            user_address = trans.sa_session.query( trans.app.model.UserAddress ).get( trans.security.decode_id( address_id ) )
        except:
            message = 'Invalid address is (%s)' % address_id
            status = 'error'
        if user_address:
            user_address.deleted = False
            trans.sa_session.flush()
            message = 'Address (%s) undeleted' % user_address.desc
            status = 'done'
        return trans.response.send_redirect( web.url_for( controller='user',
                                                          action='manage_user_info',
                                                          cntrller=cntrller,
                                                          user_id=user_id,
                                                          message=message,
                                                          status=status ) )

    @web.expose
    def set_user_pref_async( self, trans, pref_name, pref_value ):
        """ Set a user preference asynchronously. If user is not logged in, do nothing. """
        if trans.user:
            trans.log_action( trans.get_user(), "set_user_pref", "", { pref_name: pref_value } )
            trans.user.preferences[pref_name] = pref_value
            trans.sa_session.flush()

    @web.expose
    def log_user_action_async( self, trans, action, context, params ):
        """ Log a user action asynchronously. If user is not logged in, do nothing. """
        if trans.user:
            trans.log_action( trans.get_user(), action, context, params )

    @web.expose
    @web.require_login()
    def dbkeys( self, trans, **kwds ):
        """ Handle custom builds. """

        #
        # Process arguments and add/delete build.
        #
        user = trans.user
        message = None
        lines_skipped = 0
        if self.installed_len_files is None:
            installed_builds = []
            for build in glob.glob( os.path.join(trans.app.config.len_file_path, "*.len") ):
                installed_builds.append( os.path.basename(build).split(".len")[0] )
            self.installed_len_files = ", ".join(installed_builds)
        if 'dbkeys' not in user.preferences:
            dbkeys = {}
        else:
            dbkeys = loads(user.preferences['dbkeys'])
        if 'delete' in kwds:
            # Delete a build.
            key = kwds.get('key', '')
            if key and key in dbkeys:
                del dbkeys[key]
        elif 'add' in kwds:
            # Add new custom build.
            name = kwds.get('name', '')
            key = kwds.get('key', '')

            # Look for build's chrom info in len_file and len_text.
            len_file = kwds.get( 'len_file', None )
            if getattr( len_file, "file", None ):  # Check if it's a FieldStorage object
                len_text = len_file.file.read()
            else:
                len_text = kwds.get( 'len_text', None )

            if not len_text:
                # Using FASTA from history.
                dataset_id = kwds.get('dataset_id', '')

            if not name or not key or not ( len_text or dataset_id ):
                message = "You must specify values for all the fields."
            elif key in dbkeys:
                message = "There is already a custom build with that key. Delete it first if you want to replace it."
            else:
                # Have everything needed; create new build.
                build_dict = { "name": name }
                if len_text:
                    # Create new len file
                    new_len = trans.app.model.HistoryDatasetAssociation( extension="len", create_dataset=True, sa_session=trans.sa_session )
                    trans.sa_session.add( new_len )
                    new_len.name = name
                    new_len.visible = False
                    new_len.state = trans.app.model.Job.states.OK
                    new_len.info = "custom build .len file"
                    trans.sa_session.flush()
                    counter = 0
                    f = open(new_len.file_name, "w")
                    # LEN files have format:
                    #   <chrom_name><tab><chrom_length>
                    for line in len_text.split("\n"):
                        lst = line.strip().rsplit(None, 1)  # Splits at the last whitespace in the line
                        if not lst or len(lst) < 2:
                            lines_skipped += 1
                            continue
                        chrom, length = lst[0], lst[1]
                        try:
                            length = int(length)
                        except ValueError:
                            lines_skipped += 1
                            continue
                        counter += 1
                        f.write("%s\t%s\n" % (chrom, length))
                    f.close()
                    build_dict.update( { "len": new_len.id, "count": counter } )
                else:
                    dataset_id = trans.security.decode_id( dataset_id )
                    build_dict[ "fasta" ] = dataset_id
                dbkeys[key] = build_dict
        # Save builds.
        # TODO: use database table to save builds.
        user.preferences['dbkeys'] = dumps(dbkeys)
        trans.sa_session.flush()

        #
        # Display custom builds page.
        #

        # Add chrom/contig count to dbkeys dict.
        updated = False
        for key, attributes in dbkeys.items():
            if 'count' in attributes:
                # Already have count, so do nothing.
                continue

            # Get len file.
            fasta_dataset = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( attributes[ 'fasta' ] )
            len_dataset = fasta_dataset.get_converted_dataset( trans, "len" )
            # HACK: need to request dataset again b/c get_converted_dataset()
            # doesn't return dataset (as it probably should).
            len_dataset = fasta_dataset.get_converted_dataset( trans, "len" )
            if len_dataset.state == trans.app.model.Job.states.ERROR:
                # Can't use len dataset.
                continue

            # Get chrom count file.
            chrom_count_dataset = len_dataset.get_converted_dataset( trans, "linecount" )
            if not chrom_count_dataset or chrom_count_dataset.state != trans.app.model.Job.states.OK:
                # No valid linecount dataset.
                continue
            else:
                # Set chrom count.
                try:
                    chrom_count = int( open( chrom_count_dataset.file_name ).readline() )
                    attributes[ 'count' ] = chrom_count
                    updated = True
                except Exception, e:
                    log.error( "Failed to open chrom count dataset: %s", e )

        if updated:
            user.preferences['dbkeys'] = dumps(dbkeys)
            trans.sa_session.flush()

        # Potential genome data for custom builds is limited to fasta datasets in current history for now.
        fasta_hdas = trans.sa_session.query( model.HistoryDatasetAssociation ) \
                          .filter_by( history=trans.history, extension="fasta", deleted=False ) \
                          .order_by( model.HistoryDatasetAssociation.hid.desc() )

        return trans.fill_template( 'user/dbkeys.mako',
                                    user=user,
                                    dbkeys=dbkeys,
                                    message=message,
                                    installed_len_files=self.installed_len_files,
                                    lines_skipped=lines_skipped,
                                    fasta_hdas=fasta_hdas,
                                    use_panels=kwds.get( 'use_panels', False ) )

    @web.expose
    @web.require_login()
    def api_keys( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        if params.get( 'new_api_key_button', False ):
            self.create_api_key( trans, trans.user )
            message = "Generated a new web API key"
            status = "done"
        return trans.fill_template( 'webapps/galaxy/user/api_keys.mako',
                                    cntrller=cntrller,
                                    user=trans.user,
                                    message=message,
                                    status=status )

    # ===== Methods for building SelectFields  ================================
    def __build_user_type_fd_id_select_field( self, trans, selected_value ):
        # Get all the user information forms
        user_info_forms = self.get_all_forms( trans,
                                              filter=dict( deleted=False ),
                                              form_type=trans.model.FormDefinition.types.USER_INFO )
        return build_select_field( trans,
                                   objs=user_info_forms,
                                   label_attr='name',
                                   select_field_name='user_type_fd_id',
                                   initial_value='none',
                                   selected_value=selected_value,
                                   refresh_on_change=True )
