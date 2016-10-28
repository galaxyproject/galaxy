"""
API operations on User Preferences objects.
"""

import sets
import json
import logging
import datetime

from markupsafe import escape
from sqlalchemy import and_, true

from galaxy import exceptions, util
from galaxy.managers import users
from galaxy.security.validate_user_input import validate_email, validate_password, validate_publicname
from galaxy.tools.toolbox.filters import FilterFactory
from galaxy.util import docstring_trim, listify
from galaxy.util.odict import odict
from galaxy.web import _future_expose_api as expose_api
from galaxy.web.base.controller import BaseAPIController, CreatesApiKeysMixin, CreatesUsersMixin, UsesTagsMixin, BaseUIController, UsesFormDefinitionsMixin
from galaxy.web.form_builder import build_select_field, AddressField

log = logging.getLogger( __name__ )


class UserPrefAPIController( BaseAPIController, BaseUIController, UsesTagsMixin, CreatesUsersMixin, CreatesApiKeysMixin, UsesFormDefinitionsMixin ):

    def __init__(self, app):
        super(UserPrefAPIController, self).__init__(app)
        self.user_manager = users.UserManager(app)

    @expose_api
    def index( self, trans, **kwd ):
        return {
            'user_id'       : trans.security.encode_id( trans.user.id ),
            'username'      : trans.user.username,
            'email'         : trans.user.email,
            'webapp'        : trans.webapp.name,
            'remote_user'   : trans.app.config.use_remote_user,
            'openid'        : trans.app.config.enable_openid,
            'enable_quotas' : trans.app.config.enable_quotas,
            'disk_usage'    : trans.user.get_disk_usage( nice_size=True ),
            'quota'         : trans.app.quota_agent.get_quota( trans.user, nice_size=True )
        }

    @expose_api
    def get_information( self, trans, user_id, **kwd ):
        '''
        Returns user details such as public username, type, addresses, etc.
        '''
        user = self._get_user( trans, user_id )
        email = util.restore_text( kwd.get( 'email', user.email ) )
        username = util.restore_text( kwd.get( 'username', user.username ) )
        inputs = list()
        inputs.append( {
            'id'    : 'email_input',
            'name'  : 'email',
            'type'  : 'text',
            'label' : 'Email address',
            'value' : email,
            'help'  : 'If you change your email address you will receive an activation link in the new mailbox and you have to activate your account by visiting it.' } )
        if trans.webapp.name == 'galaxy':
            inputs.append( {
                'id'    : 'name_input',
                'name'  : 'username',
                'type'  : 'text',
                'label' : 'Public name',
                'value' : username,
                'help'  : 'Your public name is an identifier that will be used to generate addresses for information you share publicly. Public names must be at least three characters in length and contain only lower-case letters, numbers, and the "-" character.' } )
            type_form_id = trans.security.encode_id( user.values.form_definition.id ) if user and user.values else kwd.get( 'type_form_id', None )
            if type_form_id:
                type_form_model = trans.sa_session.query( trans.app.model.FormDefinition ).get( trans.security.decode_id( type_form_id ) )
                if type_form_model:
                    inputs.append( { 'type': 'section', 'title': 'Custom options', 'inputs': custom_form_model.to_dict() } )
            info_form_models = self.get_all_forms( trans, filter=dict( deleted=False ), form_type=trans.app.model.FormDefinition.types.USER_INFO )
            info_forms = [ f.to_dict() for f in info_form_models ]
            if info_forms:
                info_field = {
                    'type'   : 'conditional',
                    'name'   : 'user_info',
                    'cases'  : [],
                    'test_param' : {
                        'name'  : 'selected',
                        'label' : 'User information',
                        'type'  : 'select',
                        'help'  : '',
                        'data'  : []
                    }
                }
                for i, d in enumerate( info_forms ):
                    info_field[ 'test_param' ][ 'data' ].append( { 'label' : d[ 'name' ], 'value': i } )
                    info_field[ 'cases' ].append( { 'value': i, 'inputs' : d[ 'inputs' ] } )
                inputs.append( info_field )
            address_field = AddressField( '' ).to_dict()
            address_values = list()        
            for address in user.addresses:
                address_item = dict()
                address_item["short_desc"] = address.desc
                address_item["name"] = address.name
                address_item["institution"] = address.institution
	        address_item["address"] = address.address
	        address_item["city"] = address.city
	        address_item["state"] = address.state
	        address_item["postal_code"] = address.postal_code
	        address_item["country"] = address.country
                address_item["phone"] = address.phone
                address_item["address_id"] = trans.security.encode_id(address.id)
                address_values.append(address_item)
            address_repeat = { 'title': 'Address', 'name': 'address', 'type': 'repeat', 'inputs': address_field[ 'inputs' ], 'cache': [] }
            for address in address_values:
                address_inputs = []
                for input in address_repeat[ 'inputs' ]:
                    input_copy = input.copy()
                    input_copy[ 'value' ] = address.get( input[ 'name' ], None )
                    address_inputs.append( input_copy )
                address_repeat[ 'cache' ].append( address_inputs )
            inputs.append( address_repeat )
        else:
            if user.active_repositories:
                inputs.append(dict(id='name_input', name='username', label='Public name:', type='hidden', value=username, help='You cannot change your public name after you have created a repository in this tool shed.'))
            else:
                inputs.append(dict(id='name_input', name='username', label='Public name:', type='text', value=username, help='Your public name provides a means of identifying you publicly within this tool shed. Public names must be at least three characters in length and contain only lower-case letters, numbers, and the "-" character. You cannot change your public name after you have created a repository in this tool shed.'))
        return {
            'webapp'            : trans.webapp.name,
            'user_id'           : trans.security.encode_id( trans.user.id ),
            'is_admin'          : trans.user_is_admin(),
            'values'            : user.values,
            'email'             : email,
            'username'          : username,
            'addresses'         : [ address.to_dict( trans ) for address in user.addresses ],
            'inputs'            : inputs,
        }


    def _build_address_dict( self, address_id, payload ):
        ''' Build user addresses' dictionary '''
        addressdict = dict()
        for i, address in enumerate( payload ):
            if address_id == address.split("|")[0]:
                addressdict[ address.split("|")[1] ] = payload[ address ]
        return addressdict

    @expose_api
    def set_information( self, trans, user_id, **kwd ):
        '''
        Save a user's email address, public username, type, addresses etc.
        '''
        user = self._get_user( trans, user_id )
        payload = kwd.get('payload')
        user.addresses = []
        addressnames = list()
        alladdressnames = [ item for item in payload if item.find("address") > -1 ]
        for item in alladdressnames:
            name = item.split('|')[0]
            if name not in addressnames:
                addressnames.append( name )

        for each_address in addressnames:
            address = self._build_address_dict( each_address, payload ) 
            add_status = self.__add_address( trans, user_id, address )
            if( add_status['status'] == 'error' ):
                raise exceptions.MessageException( add_status['message'] )
        trans.sa_session.flush()
        return { 'message': 'User information has been updated' }


    def __add_address( self, trans, user_id, params ):
        """ Add new address """
        is_admin = trans.user_is_admin()
        if is_admin:
            if not user_id:
                return trans.show_error_message("You must specify a user to add a new address to.")
            user = trans.sa_session.query(trans.app.model.User).get(trans.security.decode_id( user_id ))
        else:
            user = trans.user
        short_desc = util.restore_text(params.get('short_desc', ''))
        name = util.restore_text(params.get('name', ''))
        institution = util.restore_text(params.get('institution', ''))
        address = util.restore_text(params.get('address', ''))
        city = util.restore_text(params.get('city', ''))
        state = util.restore_text(params.get('state', ''))
        postal_code = str(util.restore_text(params.get('postal_code', '')))
        country = util.restore_text(params.get('country', ''))
        phone = str(util.restore_text(params.get('phone', '')))

        if not trans.app.config.allow_user_creation and not is_admin:
            return trans.show_error_message('User registration is disabled.  Please contact your local Galaxy administrator for an account.')

        error_status = True
        if not short_desc:
            message = 'Enter a short description for this address'
        elif not name:
            message = 'Enter the name'
        elif not institution:
            message = 'Enter the institution associated with the user'
        elif not address:
            message = 'Enter the address'
        elif not city:
            message = 'Enter the city'
        elif not state:
            message = 'Enter the state/province/region'
        elif not postal_code:
            message = 'Enter the postal code'
        elif not country:
            message = 'Enter the country'
        else:
            error_status = False
            user_address = trans.model.UserAddress(user=user,
                                                   desc=short_desc,
                                                   name=name,
                                                   institution=institution,
                                                   address=address,
                                                   city=city,
                                                   state=state,
                                                   postal_code=postal_code,
                                                   country=country,
                                                   phone=phone)
            trans.sa_session.add(user_address)
            trans.sa_session.flush()
            return {
                'message': 'Address (%s) has been added.' % escape(user_address.desc),
                'status': 'done'
            }

        if error_status:
            return {
                'message': escape( message ),
                'status': 'error'
            }

    def __edit_info(self, trans, cntrller, kwd):
        """
        Save user information like email and public name
        """
        params = util.Params(kwd)
        is_admin = cntrller == 'admin' and trans.user_is_admin()
        message = util.restore_text(params.get('message', ''))
        status = params.get('status', 'done')
        user_id = params.get('id', None)
        save_type = params.get('save_type', None)
        if user_id and is_admin:
            user = trans.sa_session.query(trans.app.model.User).get(trans.security.decode_id(user_id))
        elif user_id and (not trans.user or trans.user.id != trans.security.decode_id(user_id)):
            message = 'Invalid user id'
            status = 'error'
            user = None
        else:
            user = trans.user
        if user and (save_type == 'login_info'):
            # Editing email and username
            email = util.restore_text(params.get('email', ''))
            username = util.restore_text(params.get('username', '')).lower()

            # Validate the new values for email and username
            message = validate_email(trans, email, user)
            if not message and username:
                message = validate_publicname(trans, username, user)
            if message:
                status = 'error'
            else:
                if (user.email != email):
                    # The user's private role name must match the user's login (email)
                    private_role = trans.app.security_agent.get_private_user_role(user)
                    private_role.name = email
                    private_role.description = 'Private role for ' + email
                    # Change the email itself
                    user.email = email
                    trans.sa_session.add_all((user, private_role))
                    trans.sa_session.flush()
                    if trans.webapp.name == 'galaxy' and trans.app.config.user_activation_on:
                        user.active = False
                        trans.sa_session.add(user)
                        trans.sa_session.flush()
                        is_activation_sent = self.send_verification_email(trans, user.email, user.username)
                        if is_activation_sent:
                            message = 'The login information has been updated with the changes.<br>Verification email has been sent to your new email address. Please verify it by clicking the activation link in the email.<br>Please check your spam/trash folder in case you cannot find the message.'
                        else:
                            message = 'Unable to send activation email, please contact your local Galaxy administrator.'
                            if trans.app.config.error_email_to is not None:
                                message += ' Contact: %s' % trans.app.config.error_email_to
                if (user.username != username):
                    user.username = username
                    trans.sa_session.add(user)
                    trans.sa_session.flush()
                message = 'The login information has been updated with the changes.'
        elif user and (save_type == 'edit_user_info'):
            # Edit user information - webapp MUST BE 'galaxy'
            user_type_fd_id = params.get('user_type_fd_id', 'none')
            if user_type_fd_id not in ['none']:
                user_type_form_definition = trans.sa_session.query(trans.app.model.FormDefinition).get(trans.security.decode_id(user_type_fd_id))
            elif user.values:
                user_type_form_definition = user.values.form_definition
            else:
                # User was created before any of the user_info forms were created
                user_type_form_definition = None
            if user_type_form_definition:
                values = self.get_form_values(trans, user,
                                              user_type_form_definition, **kwd)
            else:
                values = {}
            flush_needed = False
            if user.values:
                # Editing the user info of an existing user with existing user info
                user.values.content = values
                trans.sa_session.add(user.values)
                flush_needed = True
            elif values:
                form_values = trans.model.FormValues(user_type_form_definition, values)
                trans.sa_session.add(form_values)
                user.values = form_values
                flush_needed = True
            if flush_needed:
                trans.sa_session.add(user)
                trans.sa_session.flush()
            message = "The user information has been updated with the changes."
        if user and trans.webapp.name == 'galaxy' and is_admin:
            kwd['user_id'] = trans.security.encode_id(user.id)
        kwd['id'] = user_id
        if message:
            kwd['message'] = util.sanitize_text(message)
        if status:
            kwd['status'] = status
        # Return all data for user information page
        return self.user_info( trans, kwd )

    def __delete_address(self, trans, cntrller, kwd):
        """ Delete an address """
        address_id = kwd.get('address_id', None)
        return self.__delete_undelete_address(trans, cntrller, 'delete', address_id, kwd)

    def __undelete_address(self, trans, cntrller, kwd):
        """ Undelete an address """
        address_id = kwd.get('address_id', None)
        return self.__delete_undelete_address(trans, cntrller, 'undelete', address_id, kwd)

    def __delete_undelete_address(self, trans, cntrller, op, address_id, kwd):
        """ Delete or undelete an address based on parameter op """
        is_admin = cntrller == 'admin' and trans.user_is_admin()
        user_id = kwd.get('id', False)
        if is_admin:
            if not user_id:
                return trans.show_error_message("You must specify a user to %s an address from." % op)
            user = trans.sa_session.query(trans.app.model.User).get(trans.security.decode_id(user_id))
        else:
            user = trans.user
        try:
            user_address = trans.sa_session.query(trans.app.model.UserAddress).get(trans.security.decode_id(address_id))
        except:
            return trans.show_error_message("Invalid address id.")
        if user_address:
            if user_address.user_id != user.id:
                return trans.show_error_message("Invalid address id.")
            user_address.deleted = True if op == 'delete' else False
            trans.sa_session.add(user_address)
            trans.sa_session.flush()
            message = 'Address (%s) %sd' % (escape(user_address.desc), op)
            status = 'done'

        kwd['id'] = trans.security.encode_id(user.id)
        if message:
            kwd['message'] = util.sanitize_text(message)
        if status:
            kwd['status'] = status

        return self.user_info( trans, kwd )

    @expose_api
    def password(self, trans, user_id, payload={}, **kwd):
        """
        Allows to change a user password.
        """
        if kwd:
            password = kwd.get( 'password' )
            confirm = kwd.get( 'confirm' )
            current = kwd.get( 'current' )
            token = kwd.get( 'token' )
            token_result = None
            if token:
                # If a token was supplied, validate and set user
                token_result = trans.sa_session.query(trans.app.model.PasswordResetToken).get(token)
                if not token_result or not token_result.expiration_time > datetime.utcnow():
                    raise exceptions.MessageException('Invalid or expired password reset token, please request a new one.')
                user = token_result.user
            else:
                # The user is changing their own password, validate their current password
                user = self._get_user(trans, user_id)
                (ok, message) = trans.app.auth_manager.check_change_password(user, current)
                if not ok:
                    raise exceptions.MessageException(message)
            if user:
                # Validate the new password
                message = validate_password(trans, password, confirm)
                if message:
                    raise exceptions.MessageException(message)
                else:
                    # Save new password
                    user.set_password_cleartext(password)
                    # if we used a token, invalidate it and log the user in.
                    if token_result:
                        trans.handle_user_login(token_result.user)
                        token_result.expiration_time = datetime.utcnow()
                        trans.sa_session.add(token_result)
                    # Invalidate all other sessions
                    for other_galaxy_session in trans.sa_session.query(trans.app.model.GalaxySession) \
                                                     .filter(and_(trans.app.model.GalaxySession.table.c.user_id == user.id,
                                                                  trans.app.model.GalaxySession.table.c.is_valid == true(),
                                                                  trans.app.model.GalaxySession.table.c.id != trans.galaxy_session.id)):
                        other_galaxy_session.is_valid = False
                        trans.sa_session.add(other_galaxy_session)
                    trans.sa_session.add(user)
                    trans.sa_session.flush()
                    trans.log_event('User change password')
                    return { 'message': 'Password has been saved.' }
            raise exceptions.MessageException('Failed to determine user, access denied.')
        else:
            return { 'message': 'Password unchanged.',
                     'inputs' : [ { 'name': 'current',  'type': 'password', 'label': 'Current password' }, {
                                    'name': 'password', 'type': 'password', 'label': 'New password'     }, {
                                    'name': 'confirm',  'type': 'password', 'label': 'Confirm password' }, {
                                    'name': 'token',    'type': 'hidden',   'hidden': True, 'ignore': None } ] }

    @expose_api
    def permissions(self, trans, user_id, payload={}, **kwd):
        """
        Set the user's default permissions for the new histories
        """
        user = self._get_user( trans, user_id )
        roles = user.all_roles()
        permitted_actions = trans.app.model.Dataset.permitted_actions.items()
        if kwd:
            permissions = {}
            for index, action in permitted_actions:
                action_id = trans.app.security_agent.get_action(action.action).action
                permissions[action_id] = [trans.sa_session.query(trans.app.model.Role).get(x) for x in kwd.get( index, [] )]
            trans.app.security_agent.user_set_default_permissions(user, permissions)
            return { 'message': 'Permissions have been saved.' }
        else:
            inputs = []
            for index, action in permitted_actions:
                inputs.append({ 'type'      : 'select',
                                'multiple'  : True,
                                'optional'  : True,
                                'name'      : index,
                                'label'     : action.action,
                                'help'      : action.description,
                                'options'   : [ ( r.name, r.id ) for r in roles ],
                                'value'     : [ a.role.id for a in user.default_permissions if a.action == action.action ] })
            return { 'message': 'Permissions unchanged.', 'inputs': inputs }

    @expose_api
    def toolbox_filters(self, trans, user_id, payload={}, **kwd):
        """
        API call for fetching toolbox filters data. Toolbox filters are specified in galaxy.ini.
        The user can activate them and the choice is stored in user_preferences.
        """
        user = self._get_user(trans, user_id)
        filter_types = odict([ ('toolbox_tool_filters',    { 'title': 'Tools',    'config': trans.app.config.user_tool_filters }),
                               ('toolbox_section_filters', { 'title': 'Sections', 'config': trans.app.config.user_section_filters }),
                               ('toolbox_label_filters',   { 'title': 'Labels',   'config': trans.app.config.user_label_filters }) ])
        if kwd:
            for filter_type in filter_types:
                new_filters = []
                for prefixed_name in kwd:
                    prefix = filter_type + '|'
                    if prefixed_name.startswith(filter_type):
                        new_filters.append( prefixed_name[len(prefix):] )
                user.preferences[filter_type] = ','.join(new_filters)
            trans.sa_session.add(user)
            trans.sa_session.flush()
            return { 'message': 'Toolbox filters have been saved.' }
        else:
            saved_values = {}
            for name, value in user.preferences.items():
                if name in filter_types:
                    saved_values[ name ] = listify(value, do_strip=True)
            inputs = []
            factory = FilterFactory(trans.app.toolbox)
            for filter_type in filter_types:
                self._add_filter_inputs(factory, filter_types, inputs, filter_type, saved_values )
            return { 'message': 'Toolbox filters unchanged.', 'inputs': inputs }

    def _add_filter_inputs(self, factory, filter_types, inputs, filter_type, saved_values):
        filter_inputs = list()
        filter_values = saved_values.get( filter_type, [] )
        filter_config = filter_types[ filter_type ][ 'config' ]
        filter_title  = filter_types[ filter_type ][ 'title' ]
        for filter_name in filter_config:
            function = factory.build_filter_function(filter_name)
            filter_inputs.append({
                'type'   : 'boolean',
                'name'   : filter_name,
                'label'  : filter_name,
                'help'   : docstring_trim(function.__doc__) or 'No description available.',
                'value'  : 'true' if filter_name in filter_values else 'false',
                'ignore' : 'false'
            })
        if filter_inputs:
            inputs.append( { 'type': 'section', 'title': filter_title, 'name': filter_type, 'expanded': True, 'inputs': filter_inputs } )

    @expose_api
    def api_key(self, trans, user_id, payload={}, **kwd):
        """
        Get/Create API key.
        """
        user = self._get_user(trans, user_id)
        if kwd:
            self.create_api_key(trans, user)
            message = 'Generated a new web API key.'
        else:
            message = 'API key unchanged.'
        webapp_name = 'Galaxy' if trans.webapp.name == 'galaxy' else 'the Tool Shed'
        inputs = [ { 'name'       : 'api-key',
                     'type'       : 'text',
                     'label'      : 'Current API key:',
                     'value'      : user.api_keys[0].key if user.api_keys else 'Not available.',
                     'readonly'   : True,
                     'help'       : ' An API key will allow you to access %s via its web API. Please note that this key acts as an alternate means to access your account and should be treated with the same care as your login password.' % webapp_name } ]
        return { 'message': message, 'inputs': inputs }

    @expose_api
    def communication(self, trans, user_id, payload={}, **kwd):
        """
        Allows the user to activate/deactivate the communication server.
        """
        user = self._get_user(trans, user_id)
        enable = kwd.get('enable')
        if enable is not None:
            if enable == 'true':
                message = 'Your communication server has been activated.'
            else:
                message = 'Your communication server has been disabled.'
            user.preferences['communication_server'] = enable
            trans.sa_session.add(user)
            trans.sa_session.flush()
            return { 'message' : message }
        else:
            return { 'message' : 'Communication server settings unchanged.',
                     'inputs'  : [{ 'name'  : 'enable',
                                    'type'  : 'boolean',
                                    'label' : 'Enable communication',
                                    'value' : user.preferences.get('communication_server', 'false') }] }

    def _get_user( self, trans, user_id ):
        user = self.get_user(trans, user_id)
        if not user:
            raise exceptions.MessageException('Invalid user (%s).' % user_id)
        if user != trans.user and trans.user_is_admin():
            raise exceptions.MessageException('Access denied.')
        return user
