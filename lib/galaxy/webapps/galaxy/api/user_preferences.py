"""
API operations on User Preferences objects.
"""

import sys
import logging
import sets
import json

from markupsafe import escape
from sqlalchemy import false, and_, or_, true, func

from galaxy import exceptions, util, web
from galaxy.managers import users
from galaxy.security.validate_user_input import validate_email
from galaxy.security.validate_user_input import validate_password
from galaxy.security.validate_user_input import validate_publicname
from galaxy.tools.toolbox.filters import FilterFactory
from galaxy.util import biostar, hash_util, docstring_trim, listify
from galaxy.web import _future_expose_api as expose_api
from galaxy.util import string_as_bool
from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.web.base.controller import BaseAPIController
from galaxy.web.base.controller import CreatesApiKeysMixin
from galaxy.web.base.controller import CreatesUsersMixin
from galaxy.web.base.controller import UsesTagsMixin
from galaxy.web.base.controller import (BaseUIController,
                                        UsesFormDefinitionsMixin)
from galaxy.web.form_builder import build_select_field, CheckboxField

log = logging.getLogger( __name__ )


class UserPreferencesAPIController( BaseAPIController, BaseUIController, UsesTagsMixin, CreatesUsersMixin, CreatesApiKeysMixin, UsesFormDefinitionsMixin ):

    @expose_api
    def index( self, trans, cntrller='user_preferences', **kwd ):
        return {'user_id': trans.security.encode_id( trans.user.id ),
                'message': "",
                'username': trans.user.username,
                'email': trans.user.email,
                'webapp': trans.webapp.name,
                'remote_user': trans.app.config.use_remote_user,
                'openid': trans.app.config.enable_openid,
                'enable_quotas': trans.app.config.enable_quotas,
                'disk_usage': trans.user.get_disk_usage( nice_size=True ),
                'quota': trans.app.quota_agent.get_quota( trans.user, nice_size=True ),
               }

    def __get_user_type_form_definition( self, trans, user=None, **kwd ):
        #params = util.Params( kwd )
        if user and user.values:
            user_type_fd_id = trans.security.encode_id( user.values.form_definition.id )
        else:
            user_type_fd_id = kwd.get( 'user_type_fd_id', 'none' )
        if user_type_fd_id not in [ 'none' ]:
            user_type_form_definition = trans.sa_session.query( trans.app.model.FormDefinition ).get( trans.security.decode_id( user_type_fd_id ) )
        else:
            user_type_form_definition = None
        return user_type_form_definition

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

    def user_info(self, cntrller, trans, kwd):
        '''Manage a user's login, password, public username, type, addresses, etc.'''
        #params = util.Params( kwd )
        user_id = kwd.get( 'id', None )
        if user_id:
            user = trans.sa_session.query( trans.app.model.User ).get( trans.security.decode_id( user_id ) )
        else:
            user = trans.user
        if not user:
            raise AssertionError("The user id (%s) is not valid" % str( user_id ))
        email = util.restore_text( kwd.get( 'email', user.email ) )
        username = util.restore_text( kwd.get( 'username', '' ) )
        if not username:
            username = user.username
        message = escape( util.restore_text( kwd.get( 'message', '' ) ) )
        status = kwd.get( 'status', 'done' )
        if trans.webapp.name == 'galaxy':
            user_type_form_definition = self.__get_user_type_form_definition( trans, user=user, **kwd )
            user_type_fd_id = kwd.get( 'user_type_fd_id', 'none' )
            if user_type_fd_id == 'none' and user_type_form_definition is not None:
                user_type_fd_id = trans.security.encode_id( user_type_form_definition.id )
            user_type_fd_id_select_field = self.__build_user_type_fd_id_select_field( trans, selected_value=user_type_fd_id )
            widgets = self.__get_widgets( trans, user_type_form_definition, user=user, **kwd )
            # user's addresses
            show_filter = util.restore_text( kwd.get( 'show_filter', 'Active'  ) )
            if show_filter == 'All':
                addresses = [address for address in user.addresses]
            elif show_filter == 'Deleted':
                addresses = [address for address in user.addresses if address.deleted]
            else:
                addresses = [address for address in user.addresses if not address.deleted]
            user_info_forms = self.get_all_forms( trans,
                                                  filter=dict( deleted=False ),
                                                  form_type=trans.app.model.FormDefinition.types.USER_INFO )
            # makes the address list JSON iterable
            address_list = dict()
            index_add = 0
            for item in addresses:
                address_list[index_add] = dict()
                address_list[index_add]["desc"] = item.desc
                address_list[index_add]["html"] = item.get_html()
                address_list[index_add]["deleted"] = item.deleted
                address_list[index_add]["address_id"] = trans.security.encode_id(item.id)
                index_add = index_add + 1
    
            # makes the widget list JSON iterable
            widget_list = dict()
            index_widget = 0
            for item in widgets:
                widget_list[index_widget] = dict()
                widget_list[index_widget]["label"] = item['label']
                widget_list[index_widget]["html"] = item['widget'].get_html()
                widget_list[index_widget]["helptext"] = item['helptext']
                index_widget = index_widget + 1

            return {'cntrller': cntrller,
                    'webapp': trans.webapp.name,
                    'user_id': trans.security.encode_id( trans.user.id ),
                    'is_admin': trans.user_is_admin(),
                    'values': user.values,
                    'email': email,
                    'username': username,
                    'user_type_fd_id_select_field_options': user_type_fd_id_select_field.options,
                    'user_type_fd_id_select_html': user_type_fd_id_select_field.get_html(),
                    'user_info_forms': user_info_forms,
                    'user_type_form_definition': user_type_form_definition,
                    'user_type_fd_id': user_type_fd_id,
                    'user_type_fd_id_encoded': trans.security.encode_id( user_type_fd_id ),
                    'widgets': widget_list,
                    'addresses' : address_list,
                    'show_filter': show_filter,
                    'message': message,
                    'status': status
                   }
        else:
            return {'cntrller': cntrller,
                    'webapp': trans.webapp.name,
                    'user_id': trans.security.encode_id( trans.user.id ),
                    'is_admin': trans.user_is_admin(),
                    'active_repositories': user.active_repositories,
                    'email': email,
                    'username': username,
                    'message': message,
                    'status': status
                   }

    @expose_api
    def manage_user_info( self, trans, cntrller='user_preferences', **kwd ):
        """ Manage User Info API call """
        return self.user_info(cntrller, trans, kwd)

    @expose_api
    def edit_info( self, trans, cntrller='user_preferences', **kwd ):
        """
        API call for Edit user information = username, email or password.
        """
        params = util.Params( kwd )
        is_admin = cntrller == 'admin' and trans.user_is_admin()
        message = util.restore_text( params.get( 'message', '' ) )
        status = params.get( 'status', 'done' )
        user_id = params.get( 'id', None )
        button_type = params.get( 'button_name', None )
        
        if user_id and is_admin:
            user = trans.sa_session.query( trans.app.model.User ).get( trans.security.decode_id( user_id ) )
        elif user_id and ( not trans.user or trans.user.id != trans.security.decode_id( user_id ) ):
            message = 'Invalid user id'
            status = 'error'
            user = None
        else:
            user = trans.user
        if user and (button_type == 'login_info_button'):
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
                if ( user.email != email ):
                    # The user's private role name must match the user's login ( email )
                    private_role = trans.app.security_agent.get_private_user_role( user )
                    private_role.name = email
                    private_role.description = 'Private role for ' + email
                    # Change the email itself
                    user.email = email
                    trans.sa_session.add_all( ( user, private_role ) )
                    trans.sa_session.flush()
                    if trans.webapp.name == 'galaxy' and trans.app.config.user_activation_on:
                        user.active = False
                        trans.sa_session.add( user )
                        trans.sa_session.flush()
                        is_activation_sent = self.send_verification_email( trans, user.email, user.username )
                        if is_activation_sent:
                            message = 'The login information has been updated with the changes.<br>Verification email has been sent to your new email address. Please verify it by clicking the activation link in the email.<br>Please check your spam/trash folder in case you cannot find the message.'
                        else:
                            message = 'Unable to send activation email, please contact your local Galaxy administrator.'
                            if trans.app.config.error_email_to is not None:
                                message += ' Contact: %s' % trans.app.config.error_email_to
                if ( user.username != username ):
                    user.username = username
                    trans.sa_session.add( user )
                    trans.sa_session.flush()
                message = 'The login information has been updated with the changes.'
        elif user and (button_type == 'edit_user_info_button'):
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
        print(kwd)
        # makes a call to manage user info method
        return self.user_info(cntrller, trans, kwd)

    @expose_api
    def edit_address( self, trans, cntrller='user_preferences', **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        is_admin = cntrller == 'admin' and trans.user_is_admin()
        user_id = params.get( 'id', False )
        if is_admin:
            if not user_id:
                return trans.show_error_message( "You must specify a user to add a new address to." )
            user = trans.sa_session.query( trans.app.model.User ).get( trans.security.decode_id( user_id ) )
        else:
            user = trans.user
        address_id = params.get( 'address_id', None )
        if not address_id:
            return trans.show_error_message( "Invalid address id." )
        address_obj = trans.sa_session.query( trans.app.model.UserAddress ).get( trans.security.decode_id( address_id ) )
        if address_obj.user_id != user.id:
            return trans.show_error_message( "Invalid address id." )
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
                message = 'Address (%s) has been updated.' % escape( address_obj.desc )
                new_kwd = dict( message=message, status=status )
                if is_admin:
                    new_kwd[ 'id' ] = trans.security.encode_id( user.id )

                return self.user_info(cntrller, trans, new_kwd)
            else:
                status = 'error'

        # Display the address form with the current values filled in
        address_item = dict()
        address_item["desc"] = address_obj.desc
        address_item["name"] = address_obj.name
        address_item["institution"] = address_obj.institution 
        address_item["address"] = address_obj.address
        address_item["city"] = address_obj.city
        address_item["state"] = address_obj.state
        address_item["postal_code"] = address_obj.postal_code
        address_item["country"] = address_obj.country
        address_item["phone"] = address_obj.phone

        return {
            'user_id': user_id,
            'address_obj': address_item,
            'address_id': address_id,
            'message': escape( message ),
            'status': status
        }
    
    @expose_api
    def delete_address( self, trans, cntrller='user_preferences', address_id=None, **kwd ):
        return self.__delete_undelete_address( trans, cntrller, 'delete', address_id=address_id, **kwd )

    @expose_api
    def undelete_address( self, trans, cntrller='user_preferences', address_id=None, **kwd ):
        return self.__delete_undelete_address( trans, cntrller, 'undelete', address_id=address_id, **kwd )

    def __delete_undelete_address( self, trans, cntrller, op, address_id=None, **kwd ):
        is_admin = cntrller == 'admin' and trans.user_is_admin()
        user_id = kwd.get( 'id', False )
        if is_admin:
            if not user_id:
                return trans.show_error_message( "You must specify a user to %s an address from." % op )
            user = trans.sa_session.query( trans.app.model.User ).get( trans.security.decode_id( user_id ) )
        else:
            user = trans.user
        try:
            user_address = trans.sa_session.query( trans.app.model.UserAddress ).get( trans.security.decode_id( address_id ) )
        except:
            return trans.show_error_message( "Invalid address id." )
        if user_address:
            if user_address.user_id != user.id:
                return trans.show_error_message( "Invalid address id." )
            user_address.deleted = True if op == 'delete' else False
            trans.sa_session.add( user_address )
            trans.sa_session.flush()
            message = 'Address (%s) %sd' % ( escape( user_address.desc ), op )
            status = 'done'

        kwd[ 'id' ] = trans.security.encode_id( user.id )
        if message:
            kwd[ 'message' ] = util.sanitize_text( message )
        if status:
            kwd[ 'status' ] = status

        return self.user_info(cntrller, trans, kwd)

    @expose_api
    def new_address( self, trans, cntrller='user_preferences', **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        is_admin = cntrller == 'admin' and trans.user_is_admin()
        user_id = params.get( 'id', False )
        if is_admin:
            if not user_id:
                return trans.show_error_message( "You must specify a user to add a new address to." )
            user = trans.sa_session.query( trans.app.model.User ).get( trans.security.decode_id( user_id ) )
        else:
            user = trans.user
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
                message = 'Address (%s) has been added' % escape( user_address.desc )
                new_kwd = dict( message=message, status=status )
                if is_admin:
                    new_kwd[ 'id' ] = trans.security.encode_id( user.id )
                return self.user_info(cntrller, trans, new_kwd)
            else:
                return {
                    'user_id': user_id,
                    'message': escape( message ),
                    'status': 'error'
                }

    @expose_api
    def change_password( self, trans, password=None, confirm=None, current=None, token=None, **kwd):
        """
        Provides a form with which one can change their password. If token is
        provided, don't require current password.
        """
        user = None
        token_result = None
        if token:
            # If a token was supplied, validate and set user
            token_result = trans.sa_session.query( trans.app.model.PasswordResetToken ).get(token)
            if token_result and token_result.expiration_time > datetime.utcnow():
                user = token_result.user
            else:
                return { message: 'Invalid or expired password reset token, please request a new one.', 'status': 'error' }
        else:
            # The user is changing their own password, validate their current password
            ( ok, message ) = trans.app.auth_manager.check_change_password( trans.user, current )
            if ok:
                user = trans.user
            else:
                return { 'message': message, 'status': 'error' }
        if user:
            # Validate the new password
            message = validate_password( trans, password, confirm )
            if message:
                return { 'message': message, 'status': 'error' }
            else:
                # Save new password
                user.set_password_cleartext( password )
                # if we used a token, invalidate it and log the user in.
                if token_result:
                    trans.handle_user_login( token_result.user )
                    token_result.expiration_time = datetime.utcnow()
                    trans.sa_session.add( token_result )
                # Invalidate all other sessions
                for other_galaxy_session in trans.sa_session.query( trans.app.model.GalaxySession ) \
                                                 .filter( and_( trans.app.model.GalaxySession.table.c.user_id == user.id,
                                                                trans.app.model.GalaxySession.table.c.is_valid == true(),
                                                                trans.app.model.GalaxySession.table.c.id != trans.galaxy_session.id ) ):
                    other_galaxy_session.is_valid = False
                    trans.sa_session.add( other_galaxy_session )
                trans.sa_session.add( user )
                trans.sa_session.flush()
                trans.log_event( "User change password" )
                return { 'message': 'Password has been changed', 'status': 'done' }
        return { 'message': 'Failed to determine user, access denied', 'status': 'error' }

    @expose_api
    def set_default_permissions( self, trans, cntrller='user_preferences', **kwd ):
        """Set the user's default permissions for the new histories"""
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
                return {
                    'message': message,
                    'status': status
                }
            else:
                return self.render_permission_form( trans, message, status )

        else:
            # User not logged in, history group must be only public
            #return trans.show_error_message( "You must be logged in to change your default permitted actions." )
            return {
                'message': "You must be logged in to change your default permitted actions.",
                'status': "error"
            }

     
    def render_permission_form( self, trans, message, status, do_not_render=[], all_roles=[] ):
        ''' 
        Obtains parameters to build change permission form
        '''
        obj = trans.user
        obj_name = trans.user.email
        roles = trans.user.all_roles()
        if isinstance( obj, trans.app.model.User ):
            current_actions = obj.default_permissions
            permitted_actions = trans.app.model.Dataset.permitted_actions.items()
            obj_str = 'user %s' % obj_name
            obj_type = 'dataset'
        elif isinstance( obj, trans.app.model.History ):
            current_actions = obj.default_permissions
            permitted_actions = trans.app.model.Dataset.permitted_actions.items()
            obj_str = 'history %s' % obj_name
            obj_type = 'dataset'
        elif isinstance( obj, trans.app.model.Dataset ):
            current_actions = obj.actions
            permitted_actions = trans.app.model.Dataset.permitted_actions.items()
            obj_str = obj_name
            obj_type = 'dataset'
        elif isinstance( obj, trans.app.model.LibraryDatasetDatasetAssociation ):
            current_actions = obj.actions + obj.dataset.actions
            permitted_actions = trans.app.model.Dataset.permitted_actions.items() + trans.app.model.Library.permitted_actions.items()
            obj_str = obj_name
            obj_type = 'dataset'
        elif isinstance( obj, trans.app.model.Library ):
            current_actions = obj.actions
            permitted_actions = trans.app.model.Library.permitted_actions.items()
            obj_str = 'library %s' % obj_name
            obj_type = 'library'
        elif isinstance( obj, trans.app.model.LibraryDataset ):
            current_actions = obj.actions
            permitted_actions = trans.app.model.Library.permitted_actions.items()
            obj_str = 'library dataset %s' % obj_name
            obj_type = 'library'
        elif isinstance( obj, trans.app.model.LibraryFolder ):
            current_actions = obj.actions
            permitted_actions = trans.app.model.Library.permitted_actions.items()
            obj_str = 'library folder %s' % obj_name
            obj_type = 'library'
        else:
            current_actions = []
            permitted_actions = {}.items()
            obj_str = 'unknown object %s' % obj_name
            obj_type = ''

        # converts the list to JSON iterable
        index = 0
        current_action_list = dict()
        for item in current_actions:
            current_action_list[index] = dict()
            current_action_list[index]["action"] = item.action
            #current_action_list[index]["action_key"] = item
            index = index + 1

        index = 0
        permitted_action_list = dict()
        for item, action in permitted_actions:
            if item not in do_not_render: 
                permitted_action_list[index] = dict()
                if( item == 'LIBRARY_ACCESS' ):
                    role_list = self.get_roles_action( current_actions, permitted_actions, action, do_not_render, all_roles )
                else:
                    role_list = self.get_roles_action( current_actions, permitted_actions, action, do_not_render, roles )
	        permitted_action_list[index]["action"] = action.action
	        permitted_action_list[index]["description"] = action.description
	        permitted_action_list[index]["action_key"] = item
	        permitted_action_list[index]["in_roles"] = role_list["in_role_iterable"]
	        permitted_action_list[index]["out_roles"] = role_list["out_role_iterable"]
            index = index + 1
 
        return {
            'userid': trans.user.id,
            'current_actions': current_action_list,
            'permitted_actions': permitted_action_list,
            'obj_str': obj_str,
            'obj_type': obj_type,
            'data_access': trans.app.security_agent.permitted_actions.DATASET_ACCESS.action,
            'all_roles': all_roles,
            'message': message,
            'status': status
        }


    def get_roles_action( self, current_actions, permitted_actions, action, do_not_render, roles ):
        '''
        Fetch in and out roles based on action
        '''
        in_roles = sets.Set()
        out_roles = []
        for a in current_actions:
            if a.action == action.action:
                in_roles.add( a.role )
        out_roles = filter( lambda x: x not in in_roles, roles )
        in_role_iterable = self.get_iterable_roles( in_roles )
        out_role_iterable = self.get_iterable_roles( out_roles )
        return {
            'in_role_iterable': in_role_iterable,
            'out_role_iterable': out_role_iterable
        }


    def get_iterable_roles( self, role_list ):
        '''
        Converts list to JSON iterable list
        '''
        index = 0
        iterable_roles_list = dict()
        for item in role_list:
            iterable_roles_list[index] = dict()
            iterable_roles_list[index]["id"] = item.id
            iterable_roles_list[index]["name"] = item.name
            index = index + 1
        return iterable_roles_list


    @expose_api
    def api_keys( self, trans, cntrller='user_preferences', **kwd ):
        '''
        Generate API keys
        '''
        params = util.Params( kwd )
        message = escape( util.restore_text( params.get( 'message', ''  ) ) )
        status = params.get( 'status', 'done' )
        if params.get( 'new_api_key_button', False ):
            self.create_api_key( trans, trans.user )
            message = "Generated a new web API key"
            status = "done"

        if( trans.user.api_keys ):
            return {
                'message': message,
                'status': status,
                'has_api_key': True,
                'user_api_key': trans.user.api_keys[0].key,
                'app_name': trans.webapp.name
            }
        else:
            return {
                'message': message,
                'status': status,
                'has_api_key': False,
                'app_name': trans.webapp.name
            }


    def tool_filters( self, trans, cntrller='user_preferences', **kwd ):
        """
            Sets the user's default filters for the toolbox.
            Toolbox filters are specified in galaxy.ini.
            The user can activate them and the choice is stored in user_preferences.
        """

        def get_filter_mapping( db_filters, config_filters, factory ):
            """
                Compare the allowed filters from the galaxy.ini config file with the previously saved or default filters from the database.
                We need that to toogle the checkboxes for the formular in the right way.
                Furthermore we extract all information associated to a filter to display them in the formular.
            """
            filters = list()
            for filter_name in config_filters:
                function = factory._build_filter_function(filter_name)
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

            ff = FilterFactory(trans.app.toolbox)
            tool_filters = get_filter_mapping( saved_user_tool_filters, trans.app.config.user_tool_filters, ff )
            section_filters = get_filter_mapping( saved_user_section_filters, trans.app.config.user_section_filters, ff )
            label_filters = get_filter_mapping( saved_user_label_filters, trans.app.config.user_label_filters, ff )
            return {
                'message': message,
                'status': status,
                'tool_filters': json.dumps( tool_filters ),
                'section_filters': json.dumps( section_filters ),
                'label_filters': json.dumps( label_filters ),
            }
        else:
            # User not logged in, history group must be only public
            return {
                'message': "You must be logged in to change private toolbox filters.",
                'status': "error"
            }

    @expose_api
    def toolbox_filters( self, trans, cntrller='user_preferences', **kwd ):
        """
        API call for fetching toolbox filters data
        """
        return self.tool_filters( trans, **kwd )

    @expose_api
    def edit_toolbox_filters( self, trans, cntrller='user_preferences', **kwd ):
        """
        Saves the changes made to the toolbox filters
        """
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', '' ) )
        checked_filters = kwd.get( 'checked_filters', {} )
        checked_filters = json.loads( checked_filters )
        if params.get( 'edit_toolbox_filter_button', False ):
            tool_filters = list()
            section_filters = list()
            label_filters = list()
            for name in checked_filters:
                if( checked_filters[name] == True or checked_filters[name] == 'true'  ): 
                    name = name.split( "|" )[1]
                    if name.startswith( 't_' ):
                        tool_filters.append( name[2:] )
                    elif name.startswith( 'l_' ):
                        label_filters.append( name[2:] )
                    elif name.startswith( 's_' ):
                        section_filters.append( name[2:] )

            trans.user.preferences['toolbox_tool_filters'] = ','.join( tool_filters )
            trans.user.preferences['toolbox_section_filters'] = ','.join( section_filters )
            trans.user.preferences['toolbox_label_filters'] = ','.join( label_filters )

            trans.sa_session.add( trans.user )
            trans.sa_session.flush()
            message = 'ToolBox filters have been updated.'
            kwd = dict( message=message, status='done' )

        # Display the ToolBox filters form with the current values filled in
        return self.tool_filters( trans, **kwd )

    @expose_api
    def change_communication( self, trans, cntrller='user_preferences', **kwd):
        """
        Provides a form with which the user can activate/deactivate the commnication server.
        """
        params = util.Params( kwd )
        is_admin = cntrller == 'admin' and trans.user_is_admin()
        message = 'Communication server settings unchanged.'
        status  = 'done'
        user_id = params.get( 'user_id', None )
        if user_id and is_admin:
            user = trans.sa_session.query( trans.app.model.User ).get( trans.security.decode_id( user_id ) )
        else:
            user = trans.user
        enabled_comm = params.get( 'enable_communication_server', None )
        if user and enabled_comm is not None:
            if enabled_comm == 'true':
                message = 'Your communication server has been activated.'
            else:
                message = 'Your communication server has been disabled.'
            user.preferences[ 'communication_server' ] = enabled_comm
            trans.sa_session.add( user )
            trans.sa_session.flush()
        return {
            'message'   : message,
            'status'    : status,
            'activated' : user.preferences.get( 'communication_server', 'false' )
        }

    '''@expose_api
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
        message = 'You have been logged out.<br>To log in again <a target="_top" href="%s">go to the home page</a>.' % \
            ( url_for( '/' ) )
        if biostar.biostar_logged_in( trans ):
            biostar_url = biostar.biostar_logout( trans )
            if biostar_url:
                # TODO: It would be better if we automatically logged this user out of biostar
                message += '<br>To logout of Biostar, please click <a href="%s" target="_blank">here</a>.' % ( biostar_url )
        if trans.app.config.use_remote_user and trans.app.config.remote_user_logout_href:
            trans.response.send_redirect(trans.app.config.remote_user_logout_href)
        else:
            return {
                'message': message,
                'status': 'done'
            }
            return trans.fill_template('/user/logout.mako',
                                       refresh_frames=refresh_frames,
                                       message=message,
                                       status='done',
                                       active_view="user" )'''
