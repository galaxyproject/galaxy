"""
API operations on User Preferences objects.
"""
import logging
import datetime
import re
from sqlalchemy import and_, true
from galaxy import util
from galaxy.exceptions import MessageException
from galaxy.managers import users
from galaxy.security.validate_user_input import validate_email, validate_password, validate_publicname
from galaxy.tools.toolbox.filters import FilterFactory
from galaxy.util import docstring_trim, listify
from galaxy.util.odict import odict
from galaxy.web import _future_expose_api as expose_api
from galaxy.web.base.controller import BaseAPIController, CreatesApiKeysMixin, CreatesUsersMixin, UsesTagsMixin, BaseUIController, UsesFormDefinitionsMixin
from galaxy.web.form_builder import AddressField

log = logging.getLogger(__name__)


class UserPrefAPIController(BaseAPIController, BaseUIController, UsesTagsMixin, CreatesUsersMixin, CreatesApiKeysMixin, UsesFormDefinitionsMixin):

    def __init__(self, app):
        super(UserPrefAPIController, self).__init__(app)
        self.user_manager = users.UserManager(app)

    @expose_api
    def index(self, trans, **kwd):
        return {
            'user_id': trans.security.encode_id(trans.user.id),
            'username': trans.user.username,
            'email': trans.user.email,
            'webapp': trans.webapp.name,
            'remote_user': trans.app.config.use_remote_user,
            'openid': trans.app.config.enable_openid,
            'enable_quotas': trans.app.config.enable_quotas,
            'disk_usage': trans.user.get_disk_usage(nice_size=True),
            'quota': trans.app.quota_agent.get_quota(trans.user, nice_size=True)
        }

    @expose_api
    def get_information(self, trans, user_id, **kwd):
        '''
        Returns user details such as public username, type, addresses, etc.
        '''
        user = self._get_user(trans, user_id)
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
            info_form_id = trans.security.encode_id(user.values.form_definition.id) if user.values else None
            info_form_values = user.values.content if user.values else None
            info_form_models = self.get_all_forms(trans, filter=dict(deleted=False), form_type=trans.app.model.FormDefinition.types.USER_INFO)
            info_forms = []
            for f in info_form_models:
                values = None
                if info_form_id == trans.security.encode_id(f.id):
                    values = info_form_values
                info_forms.append(f.to_dict(user=user, values=values, security=trans.security))
            if info_forms:
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
                for i, d in enumerate(info_forms):
                    info_field['test_param']['data'].append({'label': d['name'], 'value': d['id']})
                    info_field['cases'].append({'value': d['id'], 'inputs': d['inputs']})
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
            'webapp': trans.webapp.name,
            'user_id': trans.security.encode_id(trans.user.id),
            'is_admin': trans.user_is_admin(),
            'email': email,
            'username': username,
            'addresses': [address.to_dict(trans) for address in user.addresses],
            'inputs': inputs,
        }

    @expose_api
    def set_information(self, trans, user_id, payload={}, **kwd):
        '''
        Save a user's email address, public username, type, addresses etc.
        '''
        user = self._get_user(trans, user_id)
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
        if not re.match('^[a-z0-9\-]{3,255}$', username):
            return 'Public name must contain only lowercase letters, numbers and "-". It also has to be shorter than 255 characters but longer than 2'
        if not re.match('^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$', email):
            return 'Please enter your valid email address'
        if email == '':
            return 'Please enter your email address'
        if len(email) > 255:
            return 'Email cannot be more than 255 characters in length'

    def _validate_address(self, trans, user, params):
        """ Validate address """
        if not params.get('desc'):
            MessageException('Enter a short description for this address.')
        if not params.get('name'):
            MessageException('Enter the name')
        if not params.get('institution'):
            MessageException('Enter the institution associated with the user.')
        if not params.get('address'):
            MessageException('Enter the address.')
        if not params.get('city'):
            MessageException('Enter the city.')
        if not params.get('state'):
            MessageException('Enter the state/province/region.')
        if not params.get('postal_code'):
            MessageException('Enter the postal code.')
        if not params.get('country'):
            MessageException('Enter the country.')

    @expose_api
    def password(self, trans, user_id, payload={}, **kwd):
        """
        Allows to change a user password.
        """
        if trans.get_request_method() == 'PUT':
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
                user = self._get_user(trans, user_id)
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
        else:
            return {'message': 'Password unchanged.',
                    'inputs': [ {'name': 'current', 'type': 'password', 'label': 'Current password'},
                                {'name': 'password', 'type': 'password', 'label': 'New password'},
                                {'name': 'confirm', 'type': 'password', 'label': 'Confirm password'},
                                {'name': 'token', 'type': 'hidden', 'hidden': True, 'ignore': None} ]}

    @expose_api
    def permissions(self, trans, user_id, payload={}, **kwd):
        """
        Set the user's default permissions for the new histories
        """
        user = self._get_user(trans, user_id)
        roles = user.all_roles()
        permitted_actions = trans.app.model.Dataset.permitted_actions.items()
        if trans.get_request_method() == 'PUT':
            permissions = {}
            for index, action in permitted_actions:
                action_id = trans.app.security_agent.get_action(action.action).action
                permissions[action_id] = [trans.sa_session.query(trans.app.model.Role).get(x) for x in payload.get(index, [])]
            trans.app.security_agent.user_set_default_permissions(user, permissions)
            return {'message': 'Permissions have been saved.'}
        else:
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
    def toolbox_filters(self, trans, user_id, payload={}, **kwd):
        """
        API call for fetching toolbox filters data. Toolbox filters are specified in galaxy.ini.
        The user can activate them and the choice is stored in user_preferences.
        """
        user = self._get_user(trans, user_id)
        filter_types = odict([('toolbox_tool_filters', {'title': 'Tools', 'config': trans.app.config.user_tool_filters}),
                              ('toolbox_section_filters', {'title': 'Sections', 'config': trans.app.config.user_section_filters}),
                              ('toolbox_label_filters', {'title': 'Labels', 'config': trans.app.config.user_label_filters})])
        if trans.get_request_method() == 'PUT':
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
        else:
            saved_values = {}
            for name, value in user.preferences.items():
                if name in filter_types:
                    saved_values[name] = listify(value, do_strip=True)
            inputs = []
            factory = FilterFactory(trans.app.toolbox)
            for filter_type in filter_types:
                self._add_filter_inputs(factory, filter_types, inputs, filter_type, saved_values)
            return {'message': 'Toolbox filters unchanged.', 'inputs': inputs}

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

    @expose_api
    def api_key(self, trans, user_id, payload={}, **kwd):
        """
        Get/Create API key.
        """
        user = self._get_user(trans, user_id)
        if trans.get_request_method() == 'PUT':
            self.create_api_key(trans, user)
            message = 'Generated a new web API key.'
        else:
            message = 'API key unchanged.'
        webapp_name = 'Galaxy' if trans.webapp.name == 'galaxy' else 'the Tool Shed'
        inputs = [{'name': 'api-key',
                   'type': 'text',
                   'label': 'Current API key:',
                   'value': user.api_keys[0].key if user.api_keys else 'Not available.',
                   'readonly': True,
                   'help': ' An API key will allow you to access %s via its web API. Please note that this key acts as an alternate means to access your account and should be treated with the same care as your login password.' % webapp_name}]
        return {'message': message, 'inputs': inputs}

    @expose_api
    def communication(self, trans, user_id, payload={}, **kwd):
        """
        Allows the user to activate/deactivate the communication server.
        """
        user = self._get_user(trans, user_id)
        enable = payload.get('enable')
        if enable is not None:
            if enable == 'true':
                message = 'Your communication server has been activated.'
            else:
                message = 'Your communication server has been disabled.'
            user.preferences['communication_server'] = enable
            trans.sa_session.add(user)
            trans.sa_session.flush()
            return {'message': message}
        else:
            return {'message': 'Communication server settings unchanged.',
                    'inputs': [{'name': 'enable',
                                'type': 'boolean',
                                'label': 'Enable communication',
                                'value': user.preferences.get('communication_server', 'false')}]}

    def _get_user(self, trans, user_id):
        user = self.get_user(trans, user_id)
        if not user:
            raise MessageException('Invalid user (%s).' % user_id)
        if user != trans.user and trans.user_is_admin():
            raise MessageException('Access denied.')
        return user
