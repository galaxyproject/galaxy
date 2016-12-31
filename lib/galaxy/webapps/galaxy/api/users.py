"""
API operations on User objects.
"""

import logging
import datetime
import re

from sqlalchemy import false, true, and_, or_

from galaxy import exceptions, util, web
from galaxy.exceptions import MessageException
from galaxy.managers import users
from galaxy.security.validate_user_input import validate_email
from galaxy.security.validate_user_input import validate_password
from galaxy.security.validate_user_input import validate_publicname
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.web.base.controller import BaseAPIController
from galaxy.web.base.controller import CreatesApiKeysMixin
from galaxy.web.base.controller import CreatesUsersMixin
from galaxy.web.base.controller import UsesTagsMixin
from galaxy.web.base.controller import BaseUIController
from galaxy.web.base.controller import UsesFormDefinitionsMixin
from galaxy.web.form_builder import AddressField
from galaxy.tools.toolbox.filters import FilterFactory
from galaxy.util import docstring_trim, listify
from galaxy.util.odict import odict


log = logging.getLogger( __name__ )


class UserAPIController( BaseAPIController, UsesTagsMixin, CreatesUsersMixin, CreatesApiKeysMixin, BaseUIController, UsesFormDefinitionsMixin ):

    def __init__(self, app):
        super(UserAPIController, self).__init__(app)
        self.user_manager = users.UserManager(app)
        self.user_serializer = users.UserSerializer( app )
        self.user_deserializer = users.UserDeserializer( app )

    @expose_api
    def index( self, trans, deleted='False', f_email=None, f_name=None, f_any=None, **kwd ):
        """
        GET /api/users
        GET /api/users/deleted
        Displays a collection (list) of users.

        :param deleted: (optional) If true, show deleted users
        :type  deleted: bool

        :param f_email: (optional) An email address to filter on. (Non-admin
                        users can only use this if ``expose_user_email`` is ``True`` in
                        galaxy.ini)
        :type  f_email: str

        :param f_name: (optional) A username to filter on. (Non-admin users
                       can only use this if ``expose_user_name`` is ``True`` in
                       galaxy.ini)
        :type  f_name: str

        :param f_any: (optional) Filter on username OR email. (Non-admin users
                       can use this, the email filter and username filter will
                       only be active if their corresponding ``expose_user_*`` is
                       ``True`` in galaxy.ini)
        :type  f_any: str
        """
        rval = []
        query = trans.sa_session.query( trans.app.model.User )
        deleted = util.string_as_bool( deleted )

        if f_email and (trans.user_is_admin() or trans.app.config.expose_user_email):
            query = query.filter( trans.app.model.User.email.like("%%%s%%" % f_email) )

        if f_name and (trans.user_is_admin() or trans.app.config.expose_user_name):
            query = query.filter( trans.app.model.User.username.like("%%%s%%" % f_name) )

        if f_any:
            if trans.user_is_admin():
                query = query.filter(or_(
                    trans.app.model.User.email.like("%%%s%%" % f_any),
                    trans.app.model.User.username.like("%%%s%%" % f_any)
                ))
            else:
                if trans.app.config.expose_user_email and trans.app.config.expose_user_name:
                    query = query.filter(or_(
                        trans.app.model.User.email.like("%%%s%%" % f_any),
                        trans.app.model.User.username.like("%%%s%%" % f_any)
                    ))
                elif trans.app.config.expose_user_email:
                    query = query.filter( trans.app.model.User.email.like("%%%s%%" % f_any) )
                elif trans.app.config.expose_user_name:
                    query = query.filter( trans.app.model.User.username.like("%%%s%%" % f_any) )

        if deleted:
            query = query.filter( trans.app.model.User.table.c.deleted == true() )
            # only admins can see deleted users
            if not trans.user_is_admin():
                return []
        else:
            query = query.filter( trans.app.model.User.table.c.deleted == false() )
            # special case: user can see only their own user
            # special case2: if the galaxy admin has specified that other user email/names are
            #   exposed, we don't want special case #1
            if not trans.user_is_admin() and not trans.app.config.expose_user_name and not trans.app.config.expose_user_email:
                item = trans.user.to_dict( value_mapper={ 'id': trans.security.encode_id } )
                return [item]
        for user in query:
            item = user.to_dict( value_mapper={ 'id': trans.security.encode_id } )
            # If NOT configured to expose_email, do not expose email UNLESS the user is self, or
            # the user is an admin
            if not trans.app.config.expose_user_name and user is not trans.user and not trans.user_is_admin():
                del item['username']
            if not trans.app.config.expose_user_email and user is not trans.user and not trans.user_is_admin():
                del item['email']
            # TODO: move into api_values
            rval.append( item )
        return rval

    @expose_api_anonymous
    def show( self, trans, id, deleted='False', **kwd ):
        """
        GET /api/users/{encoded_id}
        GET /api/users/deleted/{encoded_id}
        GET /api/users/current
        Displays information about a user.
        """
        deleted = util.string_as_bool( deleted )
        try:
            # user is requesting data about themselves
            if id == "current":
                # ...and is anonymous - return usage and quota (if any)
                if not trans.user:
                    item = self.anon_user_api_value( trans )
                    return item

                # ...and is logged in - return full
                else:
                    user = trans.user
            else:
                user = self.get_user( trans, id, deleted=deleted )
            # check that the user is requesting themselves (and they aren't del'd) unless admin
            if not trans.user_is_admin():
                assert trans.user == user
                assert not user.deleted
        except:
            raise exceptions.RequestParameterInvalidException( 'Invalid user id specified', id=id )
        return self.user_serializer.serialize_to_view(user, view='detailed')

    @expose_api
    def create( self, trans, payload, **kwd ):
        """
        POST /api/users
        Creates a new Galaxy user.
        """
        if not trans.app.config.allow_user_creation and not trans.user_is_admin():
            raise exceptions.ConfigDoesNotAllowException( 'User creation is not allowed in this Galaxy instance' )
        if trans.app.config.use_remote_user and trans.user_is_admin():
            user = trans.get_or_create_remote_user( remote_user_email=payload['remote_user_email'] )
        elif trans.user_is_admin():
            username = payload[ 'username' ]
            email = payload[ 'email' ]
            password = payload[ 'password' ]
            message = "\n".join( [ validate_email( trans, email ),
                                   validate_password( trans, password, password ),
                                   validate_publicname( trans, username ) ] ).rstrip()
            if message:
                raise exceptions.RequestParameterInvalidException( message )
            else:
                user = self.create_user( trans=trans, email=email, username=username, password=password )
        else:
            raise exceptions.NotImplemented()
        item = user.to_dict( view='element', value_mapper={ 'id': trans.security.encode_id,
                                                            'total_disk_usage': float } )
        return item

    @expose_api
    def update( self, trans, id, payload, **kwd ):
        """
        update( self, trans, id, payload, **kwd )
        * PUT /api/users/{id}
            updates the values for the item with the given ``id``

        :type id: str
        :param id: the encoded id of the item to update
        :type payload: dict
        :param payload: a dictionary of new attribute values

        :rtype: dict
        :returns: an error object if an error occurred or a dictionary containing
            the serialized item after any changes
        """
        current_user = trans.user
        user_to_update = self.user_manager.by_id( self.decode_id( id ) )

        # only allow updating other users if they're admin
        editing_someone_else = current_user != user_to_update
        is_admin = trans.api_inherit_admin or self.user_manager.is_admin( current_user )
        if editing_someone_else and not is_admin:
            raise exceptions.InsufficientPermissionsException( 'you are not allowed to update that user', id=id )

        self.user_deserializer.deserialize( user_to_update, payload, user=current_user, trans=trans )
        return self.user_serializer.serialize_to_view( user_to_update, view='detailed' )

    @expose_api
    @web.require_admin
    def delete( self, trans, id, **kwd ):
        """
        DELETE /api/users/{id}
        delete the user with the given ``id``

        :param id: the encoded id of the user to delete
        :type  id: str

        :param purge: (optional) if True, purge the user
        :type  purge: bool
        """
        if not trans.app.config.allow_user_deletion:
            raise exceptions.ConfigDoesNotAllowException( 'The configuration of this Galaxy instance does not allow admins to delete users.' )
        purge = util.string_as_bool(kwd.get('purge', False))
        if purge:
            raise exceptions.NotImplemented('Purge option has not been implemented yet')
        user = self.get_user(trans, id)
        self.user_manager.delete(user)
        return self.user_serializer.serialize_to_view(user, view='detailed')

    @expose_api
    @web.require_admin
    def undelete( self, trans, **kwd ):
        raise exceptions.NotImplemented()

    # TODO: move to more basal, common resource than this
    def anon_user_api_value( self, trans ):
        """
        Returns data for an anonymous user, truncated to only usage and quota_percent
        """
        usage = trans.app.quota_agent.get_usage( trans )
        percent = trans.app.quota_agent.get_percent( trans=trans, usage=usage )
        return {'total_disk_usage': int( usage ),
                'nice_total_disk_usage': util.nice_size( usage ),
                'quota_percent': percent}

    @expose_api
    def get_information(self, trans, id, **kwd):
        '''
        Returns user details such as public username, type, addresses, etc.
        '''
        user = self._get_user(trans, id)
        email = user.email
        username = user.username
        inputs = list()
        inputs.append({
            'id': 'email_input',
            'name': 'email',
            'type': 'text',
            'label': 'Email address',
            'value': email,
            'help': 'If you change your email address you will receive an activation link in the new mailbox and you have to activate your account by visiting it.'})
        if trans.webapp.name == 'galaxy':
            inputs.append({
                'id': 'name_input',
                'name': 'username',
                'type': 'text',
                'label': 'Public name',
                'value': username,
                'help': 'Your public name is an identifier that will be used to generate addresses for information you share publicly. Public names must be at least three characters in length and contain only lower-case letters, numbers, and the "-" character.'})
            info_form_models = self.get_all_forms(trans, filter=dict(deleted=False), form_type=trans.app.model.FormDefinition.types.USER_INFO)
            if info_form_models:
                info_form_id = trans.security.encode_id(user.values.form_definition.id) if user.values else None
                info_field = {
                    'type': 'conditional',
                    'name': 'info',
                    'cases': [],
                    'test_param': {
                        'name': 'form_id',
                        'label': 'User type',
                        'type': 'select',
                        'value': info_form_id,
                        'help': '',
                        'data': []
                    }
                }
                for f in info_form_models:
                    values = None
                    if info_form_id == trans.security.encode_id(f.id) and user.values:
                        values = user.values.content
                    info_form = f.to_dict(user=user, values=values, security=trans.security)
                    info_field['test_param']['data'].append({'label': info_form['name'], 'value': info_form['id']})
                    info_field['cases'].append({'value': info_form['id'], 'inputs': info_form['inputs']})
                inputs.append(info_field)
            address_inputs = [{'type': 'hidden', 'name': 'id', 'hidden': True}]
            for field in AddressField.fields():
                address_inputs.append({'type': 'text', 'name': field[0], 'label': field[1], 'help': field[2]})
            address_repeat = {'title': 'Address', 'name': 'address', 'type': 'repeat', 'inputs': address_inputs, 'cache': []}
            address_values = [address.to_dict(trans) for address in user.addresses]
            for address in address_values:
                address_cache = []
                for input in address_inputs:
                    input_copy = input.copy()
                    input_copy['value'] = address.get(input['name'])
                    address_cache.append(input_copy)
                address_repeat['cache'].append(address_cache)
            inputs.append(address_repeat)
        else:
            if user.active_repositories:
                inputs.append(dict(id='name_input', name='username', label='Public name:', type='hidden', value=username, help='You cannot change your public name after you have created a repository in this tool shed.'))
            else:
                inputs.append(dict(id='name_input', name='username', label='Public name:', type='text', value=username, help='Your public name provides a means of identifying you publicly within this tool shed. Public names must be at least three characters in length and contain only lower-case letters, numbers, and the "-" character. You cannot change your public name after you have created a repository in this tool shed.'))
        return {
            'email': email,
            'username': username,
            'addresses': [address.to_dict(trans) for address in user.addresses],
            'inputs': inputs,
        }

    @expose_api
    def set_information(self, trans, id, payload={}, **kwd):
        '''
        Save a user's email address, public username, type, addresses etc.
        '''
        user = self._get_user(trans, id)
        email = payload.get('email')
        username = payload.get('username')
        if email or username:
            message = self._validate_email_publicname(email, username) or validate_email(trans, email, user)
            if not message and username:
                message = validate_publicname(trans, username, user)
            if message:
                raise MessageException(message)
            # Update user email and user's private role name which must match
            if user.email != email:
                private_role = trans.app.security_agent.get_private_user_role(user)
                private_role.name = email
                private_role.description = 'Private role for ' + email
                user.email = email
                trans.sa_session.add(private_role)
                if trans.app.config.user_activation_on:
                    user.active = False
                    if self.send_verification_email(trans, user.email, user.username):
                        message = 'The login information has been updated with the changes.<br>Verification email has been sent to your new email address. Please verify it by clicking the activation link in the email.<br>Please check your spam/trash folder in case you cannot find the message.'
                    else:
                        message = 'Unable to send activation email, please contact your local Galaxy administrator.'
                        if trans.app.config.error_email_to is not None:
                            message += ' Contact: %s' % trans.app.config.error_email_to
                        raise MessageException(message)
            # Update public name
            if user.username != username:
                user.username = username
        # Update user custom form
        user_info_form_id = payload.get('info|form_id')
        if user_info_form_id:
            prefix = 'info|'
            user_info_form = trans.sa_session.query(trans.app.model.FormDefinition).get(trans.security.decode_id(user_info_form_id))
            user_info_values = {}
            for item in payload:
                if item.startswith(prefix):
                    user_info_values[item[len(prefix):]] = payload[item]
            form_values = trans.model.FormValues(user_info_form, user_info_values)
            trans.sa_session.add(form_values)
            user.values = form_values
        # Update user addresses
        address_dicts = {}
        address_count = 0
        for item in payload:
            match = re.match(r'^address_(?P<index>\d+)\|(?P<attribute>\S+)', item)
            if match:
                groups = match.groupdict()
                index = int(groups['index'])
                attribute = groups['attribute']
                address_dicts[index] = address_dicts.get(index) or {}
                address_dicts[index][attribute] = payload[item]
                address_count = max(address_count, index + 1)
        user.addresses = []
        for index in range(0, address_count):
            d = address_dicts[index]
            if d.get('id'):
                try:
                    user_address = trans.sa_session.query(trans.app.model.UserAddress).get(trans.security.decode_id(d['id']))
                except Exception as e:
                    raise MessageException('Failed to access user address (%s). %s' % (d['id'], e))
            else:
                user_address = trans.model.UserAddress()
                trans.log_event('User address added')
            for field in AddressField.fields():
                if str(field[2]).lower() == 'required' and not d.get(field[0]):
                    raise MessageException('Address %s: %s (%s) required.' % (index + 1, field[1], field[0]))
                setattr(user_address, field[0], str(d.get(field[0], '')))
            user_address.user = user
            user.addresses.append(user_address)
            trans.sa_session.add(user_address)
        trans.sa_session.add(user)
        trans.sa_session.flush()
        trans.log_event('User information added')
        return {'message': 'User information has been saved.'}

    def _validate_email_publicname(self, email, username):
        ''' Validate email and username using regex '''
        if email == '' or not isinstance( email, basestring ):
            return 'Please provide your email address.'
        if not re.match('^[a-z0-9\-]{3,255}$', username):
            return 'Public name must contain only lowercase letters, numbers and "-". It also has to be shorter than 255 characters but longer than 2.'
        if not re.match('^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$', email):
            return 'Please provide your valid email address.'
        if len(email) > 255:
            return 'Email cannot be more than 255 characters in length.'

    @expose_api
    def get_password(self, trans, id, payload={}, **kwd):
        """
        Return available password inputs.
        """
        return {'message': 'Password unchanged.',
                'inputs': [ {'name': 'current', 'type': 'password', 'label': 'Current password'},
                            {'name': 'password', 'type': 'password', 'label': 'New password'},
                            {'name': 'confirm', 'type': 'password', 'label': 'Confirm password'},
                            {'name': 'token', 'type': 'hidden', 'hidden': True, 'ignore': None} ]}

    @expose_api
    def set_password(self, trans, id, payload={}, **kwd):
        """
        Allows to change a user password.
        """
        password = payload.get('password')
        confirm = payload.get('confirm')
        current = payload.get('current')
        token = payload.get('token')
        token_result = None
        if token:
            # If a token was supplied, validate and set user
            token_result = trans.sa_session.query(trans.app.model.PasswordResetToken).get(token)
            if not token_result or not token_result.expiration_time > datetime.utcnow():
                raise MessageException('Invalid or expired password reset token, please request a new one.')
            user = token_result.user
        else:
            # The user is changing their own password, validate their current password
            user = self._get_user(trans, id)
            (ok, message) = trans.app.auth_manager.check_change_password(user, current)
            if not ok:
                raise MessageException(message)
        if user:
            # Validate the new password
            message = validate_password(trans, password, confirm)
            if message:
                raise MessageException(message)
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
                return {'message': 'Password has been saved.'}
        raise MessageException('Failed to determine user, access denied.')

    @expose_api
    def get_permissions(self, trans, id, payload={}, **kwd):
        """
        Get the user's default permissions for the new histories
        """
        user = self._get_user(trans, id)
        roles = user.all_roles()
        permitted_actions = trans.app.model.Dataset.permitted_actions.items()
        inputs = []
        for index, action in permitted_actions:
            inputs.append({'type': 'select',
                           'multiple': True,
                           'optional': True,
                           'name': index,
                           'label': action.action,
                           'help': action.description,
                           'options': [(r.name, r.id) for r in roles],
                           'value': [a.role.id for a in user.default_permissions if a.action == action.action]})
        return {'message': 'Permissions unchanged.', 'inputs': inputs}

    @expose_api
    def set_permissions(self, trans, id, payload={}, **kwd):
        """
        Set the user's default permissions for the new histories
        """
        user = self._get_user(trans, id)
        permitted_actions = trans.app.model.Dataset.permitted_actions.items()
        permissions = {}
        for index, action in permitted_actions:
            action_id = trans.app.security_agent.get_action(action.action).action
            permissions[action_id] = [trans.sa_session.query(trans.app.model.Role).get(x) for x in (payload.get(index) or [])]
        trans.app.security_agent.user_set_default_permissions(user, permissions)
        return {'message': 'Permissions have been saved.'}

    @expose_api
    def get_toolbox_filters(self, trans, id, payload={}, **kwd):
        """
        API call for fetching toolbox filters data. Toolbox filters are specified in galaxy.ini.
        The user can activate them and the choice is stored in user_preferences.
        """
        user = self._get_user(trans, id)
        filter_types = self._get_filter_types(trans)
        saved_values = {}
        for name, value in user.preferences.items():
            if name in filter_types:
                saved_values[name] = listify(value, do_strip=True)
        inputs = []
        factory = FilterFactory(trans.app.toolbox)
        for filter_type in filter_types:
            self._add_filter_inputs(factory, filter_types, inputs, filter_type, saved_values)
        return {'message': 'Toolbox filters unchanged.', 'inputs': inputs}

    @expose_api
    def set_toolbox_filters(self, trans, id, payload={}, **kwd):
        """
        API call to update toolbox filters data.
        """
        user = self._get_user(trans, id)
        filter_types = self._get_filter_types(trans)
        for filter_type in filter_types:
            new_filters = []
            for prefixed_name in payload:
                prefix = filter_type + '|'
                if prefixed_name.startswith(filter_type):
                    new_filters.append(prefixed_name[len(prefix):])
            user.preferences[filter_type] = ','.join(new_filters)
        trans.sa_session.add(user)
        trans.sa_session.flush()
        return {'message': 'Toolbox filters have been saved.'}

    def _add_filter_inputs(self, factory, filter_types, inputs, filter_type, saved_values):
        filter_inputs = list()
        filter_values = saved_values.get(filter_type, [])
        filter_config = filter_types[filter_type]['config']
        filter_title = filter_types[filter_type]['title']
        for filter_name in filter_config:
            function = factory.build_filter_function(filter_name)
            filter_inputs.append({
                'type': 'boolean',
                'name': filter_name,
                'label': filter_name,
                'help': docstring_trim(function.__doc__) or 'No description available.',
                'value': 'true' if filter_name in filter_values else 'false',
                'ignore': 'false'
            })
        if filter_inputs:
            inputs.append({'type': 'section', 'title': filter_title, 'name': filter_type, 'expanded': True, 'inputs': filter_inputs})

    def _get_filter_types(self, trans):
        return odict([('toolbox_tool_filters', {'title': 'Tools', 'config': trans.app.config.user_tool_filters}),
                      ('toolbox_tool_section_filters', {'title': 'Sections', 'config': trans.app.config.user_tool_section_filters}),
                      ('toolbox_tool_label_filters', {'title': 'Labels', 'config': trans.app.config.user_tool_label_filters})])

    @expose_api
    def api_key(self, trans, id, payload={}, **kwd):
        """
        Create API key.
        """
        user = self._get_user(trans, id)
        return self.create_api_key(trans, user)

    @expose_api
    def get_api_key(self, trans, id, payload={}, **kwd):
        """
        Get API key inputs.
        """
        user = self._get_user(trans, id)
        return self._build_inputs_api_key(user)

    @expose_api
    def set_api_key(self, trans, id, payload={}, **kwd):
        """
        Get API key inputs with new API key.
        """
        user = self._get_user(trans, id)
        self.create_api_key(trans, user)
        return self._build_inputs_api_key(user, message='Generated a new web API key.')

    def _build_inputs_api_key(self, user, message='' ):
        """
        Build API key inputs.
        """
        inputs = [{'name': 'api-key',
                   'type': 'text',
                   'label': 'Current API key:',
                   'value': user.api_keys[0].key if user.api_keys else 'Not available.',
                   'readonly': True,
                   'help': ' An API key will allow you to access via web API. Please note that this key acts as an alternate means to access your account and should be treated with the same care as your login password.'}]
        return {'message': message, 'inputs': inputs}

    @expose_api
    def get_communication(self, trans, id, payload={}, **kwd):
        """
        Build communication server inputs.
        """
        user = self._get_user(trans, id)
        return {'message': 'Communication server settings unchanged.',
                'inputs': [{'name': 'enable',
                            'type': 'boolean',
                            'label': 'Enable communication',
                            'value': user.preferences.get('communication_server', 'false')}]}

    @expose_api
    def set_communication(self, trans, id, payload={}, **kwd):
        """
        Allows the user to activate/deactivate the communication server.
        """
        user = self._get_user(trans, id)
        enable = payload.get('enable', 'false')
        if enable == 'true':
            message = 'Your communication server has been activated.'
        else:
            message = 'Your communication server has been disabled.'
        user.preferences['communication_server'] = enable
        trans.sa_session.add(user)
        trans.sa_session.flush()
        return {'message': message}

    def _get_user(self, trans, id):
        user = self.get_user(trans, id)
        if not user:
            raise MessageException('Invalid user (%s).' % id)
        if user != trans.user and not trans.user_is_admin():
            raise MessageException('Access denied.')
        return user
