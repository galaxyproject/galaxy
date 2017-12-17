from ..authnz import IdentityProvider
from ..model import UserAuthnzToken, PSANonce, PSAAssociation, PSAPartial, PSACode

from galaxy.web import url_for

from social_core.actions import do_auth, do_complete, do_disconnect
from social_core.backends.utils import get_backend
from social_core.strategy import BaseStrategy
from social_core.utils import setting_name, module_member
from sqlalchemy.exc import IntegrityError


DEFAULTS = {
    'STRATEGY': 'Strategy',
    'STORAGE': 'Storage'
}
# key: a component name which PSA requests.
# value: is the name of a class associated with that key.

BACKENDS = {
    'google': 'social_core.backends.google_openidconnect.GoogleOpenIdConnect'
}

BACKENDS_NAME = {
    'google': 'google-openidconnect'
}

# NOTE: a PSA backend is not initialized at the time of initializing PSAAuthnz because PSA backends have the
# following line in the initialization which obviously requires session data, and given that PSAAuthnz is initialized
# when loading Galaxy application, and at this point session does not exist, hence we can not pass session data
# at initialization to the backend, which results in backend crash.
# self.data = self.strategy.request_data()


# 'SOCIAL_AUTH_GOOGLE_OPENIDCONNECT_SECRET': 'nx3j4Z-IkIW051dJ1DObAmUs',
# 'SOCIAL_AUTH_LOGIN_REDIRECT_URL': '/done/'
# 'SOCIAL_AUTH_AUTHENTICATION_BACKENDS': ('social_core.backends.google_openidconnect.GoogleOpenIdConnect',
#                                         'social_core.backends.instagram.InstagramOAuth2'),
# 'SOCIAL_AUTH_USER_MODEL': 'models.User'
# 'SOCIAL_AUTH_GOOGLE_OPENIDCONNECT_KEY': '893677542423-5g3s0n6m1bj6fnbo739irsk7bt5os83j.apps.googleusercontent.com',
# 'SOCIAL_AUTH_PIPELINE': ('social_core.pipeline.social_auth.social_details',
#                          'social_core.pipeline.social_auth.social_uid',
#                          'social_core.pipeline.social_auth.auth_allowed',
#                          'social_core.pipeline.social_auth.social_user',
#                          'social_core.pipeline.user.get_username',
#                          'common.pipeline.require_email',
#                          'social_core.pipeline.mail.mail_validation',
#                          'social_core.pipeline.user.create_user',
#                          'social_core.pipeline.social_auth.associate_user',
#                          'social_core.pipeline.debug.debug',
#                          'social_core.pipeline.social_auth.load_extra_data',
#                          'social_core.pipeline.user.user_details',
#                          'social_core.pipeline.debug.debug')
#
#
# names:
# STRATEGY
# STORAGE
# AUTHENTICATION_BACKENDS

config = {}
config[setting_name('USER_MODEL')] = 'models.User'


class PSAAuthnz(IdentityProvider):
    def __init__(self, provider, oidc_config, oidc_backend_config):
        config['provider'] = provider.lower()

        for key, value in oidc_config.iteritems():
            config[setting_name(key)] = value

        config[setting_name('AUTHENTICATION_BACKENDS')] = (BACKENDS[provider],)

        # The following config sets PSA to call the `login_user` function for
        # logging in a user. If this setting is set to false, the `login_user`
        # would not be called, and as a result Galaxy would not know who is
        # the just logged-in user.
        config[setting_name('INACTIVE_USER_LOGIN')] = True

        if provider == 'google':
            self._setup_google_backend(oidc_backend_config)

    def _setup_google_backend(self, oidc_backend_config):
        config[setting_name('AUTH_EXTRA_ARGUMENTS')] = {'access_type': 'offline'}
        config['SOCIAL_AUTH_GOOGLE_OPENIDCONNECT_KEY'] = oidc_backend_config.get('client_id')
        config['SOCIAL_AUTH_GOOGLE_OPENIDCONNECT_SECRET'] = oidc_backend_config.get('client_secret')
        config['redirect_uri'] = oidc_backend_config.get('redirect_uri')
        if oidc_backend_config.get('prompt') is not None:
            config[setting_name('AUTH_EXTRA_ARGUMENTS')]['prompt'] = oidc_backend_config.get('prompt')

    def _on_the_fly_config(self, trans):
        trans.app.model.PSACode.trans = trans
        trans.app.model.UserAuthnzToken.trans = trans
        trans.app.model.PSANonce.trans = trans
        trans.app.model.PSAPartial.trans = trans
        trans.app.model.PSAAssociation.trans = trans
        config[setting_name('LOGIN_REDIRECT_URL')] = url_for('/')

    def get_helper(self, name, do_import=False):
        this_config = config.get(setting_name(name), DEFAULTS.get(name, None))
        return do_import and module_member(this_config) or this_config

    def get_current_user(self, trans):
        return trans.user if trans.user is not None else None

    def load_backend(self, strategy, redirect_uri):
        backends = self.get_helper('AUTHENTICATION_BACKENDS')
        backend = get_backend(backends, BACKENDS_NAME[config['provider']])
        return backend(strategy, redirect_uri)

    def login_user(self, backend, user, social_user):
        config['user'] = user

    def authenticate(self, trans):
        self._on_the_fly_config(trans)
        strategy = Strategy(trans, Storage)
        backend = self.load_backend(strategy, config['redirect_uri'])
        backend.redirect_uri = config['redirect_uri']
        return do_auth(backend)

    def callback(self, state_token, authz_code, trans):
        self._on_the_fly_config(trans)
        strategy = Strategy(trans, Storage)  # self.load_strategy()
        strategy.session_set(BACKENDS_NAME[config['provider']]+'_state', state_token)
        backend = self.load_backend(strategy, config['redirect_uri'])
        backend.redirect_uri = config['redirect_uri']
        # this is also temp; it is required in login_user. Find a method around using login_user -- I should not need it -- then remove the following line.
        self.trans = trans
        redirect_url = do_complete(backend, login=lambda backend, user, social_user: self.login_user(backend, user, social_user), user=self.get_current_user(trans), state=state_token)
        return redirect_url, config.get('user', None)

    def disconnect(self, provider, trans, redirect_url=None, association_id=None):
        self._on_the_fly_config(trans)
        uri = '/authn/{provider}/callback'  # TODO find a better of doing this -- this info should be passed from buildapp.py

        config[setting_name('DISCONNECT_REDIRECT_URL')] = redirect_url if redirect_url is not None else ()
        self.strategy = Strategy(trans, Storage)  # self.load_strategy()
        # the following line is temporary, find a better solution.
        self.backend = self.load_backend(self.strategy, uri)
        # TODO: Google requires all the redirect URIs to start with http[s]; however, eventhough the redirect uri
        # in the config starts with http, PSA removes the http prefix, and this causes authentication failing on
        # google. The following is a temporary patch. This problem should be solved properly.
        # might be able to the following using absolute_uri function in the strategy
        self.backend.redirect_uri = "http://" + self.backend.redirect_uri
        # this is also temp; it is required in login_user. Find a method around using login_user -- I should not need it -- then remove the following line.
        self.trans = trans
        return do_disconnect(self.backend, self.get_current_user(trans), association_id)


class Strategy(BaseStrategy):

    def __init__(self, trans, storage, tpl=None):
        self.trans = trans
        self.request = trans.request
        self.session = trans.session if trans.session else {}
        config['SOCIAL_AUTH_PIPELINE'] = AUTH_PIPELINE
        config['DISCONNECT_PIPELINE'] = DISCONNECT_PIPELINE

        # Both the following are fine
        # config['SOCIAL_AUTH_GOOGLE_OPENIDCONNECT_ID_TOKEN_MAX_AGE'] = 3600
        config['ID_TOKEN_MAX_AGE'] = 3600

        config['SOCIAL_AUTH_REDIRECT_IS_HTTPS'] = True if self.trans.request.host.startswith('https:') else False
        super(Strategy, self).__init__(storage, tpl)

    # Settings
    def get_setting(self, name):
        """Return value for given setting name"""
        print '\n', ('>' * 50)
        print '\tasking for: ', name
        print '\treturning : ', config[name]
        return config[name]

    # Session
    def session_get(self, name, default=None):
        """Return session value for given key"""
        return self.session.get(name, default)

    def session_set(self, name, value):
        """Set session value for given key"""
        self.session[name] = value

    def session_pop(self, name):
        """Pop session value for given key"""
        raise NotImplementedError('Not implemented D')

    # Requests
    def request_data(self, merge=True):
        """Return current request data (POST or GET)"""
        if not self.request:
            return {}
        if merge:
            data = self.request.GET.copy()
            data.update(self.request.POST)
        elif self.request.method == 'POST':
            data = self.request.POST
        else:
            data = self.request.GET
        return data

    def request_host(self):
        """Return current host value"""
        if self.request:
            return self.request.host

    def build_absolute_uri(self, path=None):
        """Build absolute URI with given (optional) path"""
        # TODO: find a better way to do this: (A) get 'google' from some config, (B) is using trans.request.host a correct method of getting galaxy address ?
        path = path or ''
        return self.trans.request.host + path.replace('{provider}', 'google')

    # Response
    def html(self, content):
        """Return HTTP response with given content"""
        raise NotImplementedError('Implement in subclass HH')

    def redirect(self, url):
        """Return a response redirect to the given URL"""
        return url

    def render_html(self, tpl=None, html=None, context=None):
        """Render given template or raw html with given context"""
        raise NotImplementedError('Implement in subclass JJ')

    def start(self):
        # Clean any partial pipeline info before starting the process
        self.clean_partial_pipeline()
        if self.backend.uses_redirect():
            return self.redirect(self.backend.auth_url())
        else:
            return self.html(self.backend.auth_html())

    def complete(self, *args, **kwargs):
        return self.backend.auth_complete(*args, **kwargs)

    def continue_pipeline(self, *args, **kwargs):
        return self.backend.continue_pipeline(*args, **kwargs)

    # TODO: a function very similar to this exists in the basestrategy, check if I need this implementation or that.
    # def authenticate(self, *args, **kwargs):
    #     kwargs['strategy'] = self
    #     kwargs['storage'] = self.storage
    #     kwargs['backend'] = self.backend
    #     return self.backend.authenticate(*args, **kwargs)

    # TODO: basestrategy implements these function as the following, update them to get galaxy user instead.
    # def create_user(self, *args, **kwargs):
    #     return self.storage.user.create_user(*args, **kwargs)
    #
    # def get_user(self, *args, **kwargs):
    #     return self.storage.user.get_user(*args, **kwargs)

    # TODO: not sure if I need these three functions in my strategy.
    # def partial_to_session(self, next, backend, request=None, *args, **kwargs):
    #     user = kwargs.get('user')
    #     social = kwargs.get('social')
    #     clean_kwargs = {
    #         'response': kwargs.get('response') or {},
    #         'details': kwargs.get('details') or {},
    #         'username': kwargs.get('username'),
    #         'uid': kwargs.get('uid'),
    #         'is_new': kwargs.get('is_new') or False,
    #         'new_association': kwargs.get('new_association') or False,
    #         'user': user and user.id or None,
    #         'social': social and {
    #             'provider': social.provider,
    #             'uid': social.uid
    #         } or None
    #     }
    #     clean_kwargs.update(kwargs)
    #     # Clean any MergeDict data type from the values
    #     clean_kwargs.update((name, dict(value))
    #                             for name, value in clean_kwargs.items()
    #                                 if isinstance(value, dict))
    #     return {
    #         'next': next,
    #         'backend': backend.name,
    #         'args': tuple(map(self.to_session_value, args)),
    #         'kwargs': dict((key, self.to_session_value(val))
    #                             for key, val in clean_kwargs.items()
    #                                if isinstance(val, self.SERIALIZABLE_TYPES))
    #     }
    #
    # def partial_from_session(self, session):
    #     kwargs = session['kwargs'].copy()
    #     user = kwargs.get('user')
    #     social = kwargs.get('social')
    #     if isinstance(social, dict):
    #         kwargs['social'] = self.storage.user.get_social_auth(**social)
    #     if user:
    #         kwargs['user'] = self.storage.user.get_user(user)
    #     return (
    #         session['next'],
    #         session['backend'],
    #         list(map(self.from_session_value, session['args'])),
    #         dict((key, self.from_session_value(val))
    #                 for key, val in kwargs.items())
    #     )
    #
    # def clean_partial_pipeline(self, name='partial_pipeline'):
    #     self.session_pop(name)



class Storage:
    user = UserAuthnzToken
    nonce = PSANonce
    association = PSAAssociation
    code = PSACode
    partial = PSAPartial

    @classmethod
    def is_integrity_error(cls, exception):
        return exception.__class__ is IntegrityError


AUTH_PIPELINE = (
    # Get the information we can about the user and return it in a simple
    # format to create the user instance later. On some cases the details are
    # already part of the auth response from the provider, but sometimes this
    # could hit a provider API.
    'social_core.pipeline.social_auth.social_details',

    # Get the social uid from whichever service we're authing thru. The uid is
    # the unique identifier of the given user in the provider.
    'social_core.pipeline.social_auth.social_uid',

    # Verifies that the current auth process is valid within the current
    # project, this is where emails and domains whitelists are applied (if
    # defined).
    'social_core.pipeline.social_auth.auth_allowed',

    # Checks if the current social-account is already associated in the site.
    'social_core.pipeline.social_auth.social_user',

    # Make up a username for this person, appends a random string at the end if
    # there's any collision.
    'social_core.pipeline.user.get_username',

    # Send a validation email to the user to verify its email address.
    # 'social_core.pipeline.mail.mail_validation',

    # Associates the current social details with another user account with
    # a similar email address.
    # 'social_core.pipeline.social_auth.associate_by_email',

    # Create a user account if we haven't found one yet.
    'social_core.pipeline.user.create_user',

    # Create the record that associated the social account with this user.
    'social_core.pipeline.social_auth.associate_user',

    # Populate the extra_data field in the social record with the values
    # specified by settings (and the default ones like access_token, etc).
    'social_core.pipeline.social_auth.load_extra_data',

    # Update the user record with any changed info from the auth service.
    'social_core.pipeline.user.user_details'
)


DISCONNECT_PIPELINE = (
    'galaxy.authnz.psa_authnz.allowed_to_disconnect',
    'galaxy.authnz.psa_authnz.disconnect'
)


def create_user(strategy, details, backend, user=None, *args, **kwargs):
    print '\n\n', '@' * 50
    if user:
        return {'is_new': False}

    fields = dict((name, kwargs.get(name, details.get(name)))
                  for name in backend.setting('USER_FIELDS', USER_FIELDS))
    if not fields:
        return

    return {
        'is_new': True,
        'user': strategy.create_user(**fields)
    }


def allowed_to_disconnect(name=None, user=None, user_storage=None, strategy=None,
                          backend=None, request=None, details=None, **kwargs):
    """
    Disconnect is the process of disassociating a Galaxy user and a third-party authnz.
    In other words, it is the process of removing any access and/or ID tokens of a user.
    This function should raise an exception if disconnection is NOT permitted. Do NOT
    return any value (except an empty dictionary) if disconnect is allowed. Because, at
    least until PSA social_core v.1.5.0, any returned value (e.g., Boolean) will result
    in ignoring the rest of the disconnect pipeline.
    See the following condition in `run_pipeline` function:
    https://github.com/python-social-auth/social-core/blob/master/social_core/backends/base.py#L114
    :param name: name of the backend (e.g., google-openidconnect)
    :type user: galaxy.model.User
    :type user_storage: galaxy.model.UserAuthnzToken
    :type strategy: galaxy.authnz.psa_authnz.Strategy
    :type backend: PSA backend object (e.g., social_core.backends.google_openidconnect.GoogleOpenIdConnect)
    :type request: webob.multidict.MultiDict
    :type details: dict
    :return: empty dict
    """
    pass


def disconnect(name=None, user=None, user_storage=None, strategy=None,
               backend=None, request=None, details=None, **kwargs):
    """
    Disconnect is the process of disassociating a Galaxy user and a third-party authnz.
    In other words, it is the process of removing any access and/or ID tokens of a user.
    :param name: name of the backend (e.g., google-openidconnect)
    :type user: galaxy.model.User
    :type user_storage: galaxy.model.UserAuthnzToken
    :type strategy: galaxy.authnz.psa_authnz.Strategy
    :type backend: PSA backend object (e.g., social_core.backends.google_openidconnect.GoogleOpenIdConnect)
    :type request: webob.multidict.MultiDict
    :type details: dict
    """
    user_authnz = strategy.trans.sa_session.query(user_storage).filter(user_storage.table.c.user_id == user.id,
                                                                       user_storage.table.c.provider == name).first()
    # TODO: log the following message, and properly return it to the endpoint and inform user.
    if user_authnz is None:
        return 'Not authenticated by any identity providers.'
    # option A
    strategy.trans.sa_session.delete(user_authnz)
    # option B
    # user_authnz.extra_data = None
    strategy.trans.sa_session.flush()
