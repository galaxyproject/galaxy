from ..authnz import IdentityProvider

from social_core import *
from social_core.backends.google_openidconnect import *

import time
import random
import hashlib

import six

from social_core.actions import do_auth, do_complete, do_disconnect
from social_core.utils import setting_name, module_member, get_strategy
from social_core.store import OpenIdStore, OpenIdSessionWrapper
from social_core.pipeline import DEFAULT_AUTH_PIPELINE, DEFAULT_DISCONNECT_PIPELINE
from social_core.strategy import BaseStrategy
from social_core.backends.utils import get_backend, user_backends_data


DEFAULTS = {
    'STRATEGY': 'Strategy',
    'STORAGE': 'Storage'
}


# TODO: State token
# you can use `state_token` function of backends to generate a state token. You don't need to generate this token
# as it is generated automatically if missing. However, generate the token using `state_token` function and save
# the token in galaxy database may be a good idea.



# TODO: This code works only by commenting out "cls._session().commit()" from "social_storage_sqlalchemy"
# maybe a better solution is to write "social_storage_sqlalchemy" in Galaxy and avoid the aforementioned line.
# Otherwise, Galaxy SQLAlchemy session maker should have "autocommit=false"; this would be a rather radical
# approach as it would break a lot of Galaxy functionality which assume a transaction is auto-committed.






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
    def __init__(self, provider, config_xml):
        self._parse_config(config_xml)

    def _parse_config(self, config_xml):

        auth_uri = config_xml.find('auth_uri')
        token_uri = config_xml.find('token_uri')

        config[setting_name('AUTHENTICATION_BACKENDS')] = (
            'social_core.backends.google_openidconnect.GoogleOpenIdConnect',
            'social_core.backends.instagram.InstagramOAuth2'
        )

        config['SOCIAL_AUTH_GOOGLE_OPENIDCONNECT_KEY'] = config_xml.find('client_id').text
        config['SOCIAL_AUTH_GOOGLE_OPENIDCONNECT_SECRET'] = config_xml.find('client_secret').text

    # def load_strategy(self):
    #    print '#' * 50, "strategy helper: {}, storage helper: {}". format(type(self.get_helper('STRATEGY')), type(self.get_helper('STORAGE')))
    #    return get_strategy(self.get_helper('STRATEGY'), self.get_helper('STORAGE'))

    def get_helper(self, name, do_import=False):
        this_config = config.get(setting_name(name),
                                DEFAULTS.get(name, None))
        return do_import and module_member(this_config) or this_config

    def get_current_user(self, trans):
        if not hasattr(self, '_user'):
            # if trans.session.get('logged_in'):
            if self.strategy.session_get('logged_in'):
                # self._user = self.strategy.get_user(trans.session.get('user_id'))
                self._user = self.strategy.session_get('user_id')
            else:
                self._user = None
        return self._user

    def load_backend(self, strategy, name, redirect_uri):
        backends = self.get_helper('AUTHENTICATION_BACKENDS')
        backend = get_backend(backends, name)
        return backend(strategy, redirect_uri)

    def login_user(self, user):
        self.strategy.session_set("logged_in", True)
        self.strategy.session_set("user_id", self.trans.user)


    def authenticate(self, trans):
        # uri = redirect_uri
        # strategy = Strategy()
        # print '\n', GoogleOpenIdConnect(strategy=strategy, redirect_uri=None)
        uri = '/authn/{provider}/callback'  # TODO find a better of doing this -- this info should be passed from buildapp.py
        # TODO: do something like the following for all the providers.
        # if client_secret_file is None:
        #    log.error("Did not find `client_secret_file` key in the configuration; skipping the node '{}'."
        # .format(config.get('name')))
        #    raise ParseError

        backend_label = 'google-openidconnect'
        self.strategy = Strategy(trans, Storage)  # self.load_strategy()
        self.backend = self.load_backend(self.strategy, backend_label, uri)
        # print '\n\nbackend: {}\ndir: {}\n\n\nbackend redirect_uri: {}\n\n'.format(self.backend, dir(self.backend), self.backend.redirect_uri)
        # TODO: Google requires all the redirect URIs to start with http[s]; however, eventhough the redirect uri
        # in the config starts with http, PSA removes the http prefix, and this causes authentication failing on
        # google. The following is a temporary patch. This problem should be solved properly.
        # might be able to the following using absolute_uri function in the strategy
        self.backend.redirect_uri = "http://" + self.backend.redirect_uri
        return do_auth(self.backend)

    def callback(self, state_token, authz_code, trans):
        uri = '/authn/{provider}/callback'  # TODO find a better of doing this -- this info should be passed from buildapp.py
        backend_label = 'google-openidconnect'
        self.strategy = Strategy(trans, Storage)  # self.load_strategy()
        # the following line is temporary, find a better solution.
        self.strategy.session_set('google-openidconnect_state', state_token)
        self.backend = self.load_backend(self.strategy, backend_label, uri)
        # TODO: Google requires all the redirect URIs to start with http[s]; however, eventhough the redirect uri
        # in the config starts with http, PSA removes the http prefix, and this causes authentication failing on
        # google. The following is a temporary patch. This problem should be solved properly.
        # might be able to the following using absolute_uri function in the strategy
        self.backend.redirect_uri = "http://" + self.backend.redirect_uri
        # this is also temp; it is required in login_user. Find a method around using login_user -- I should not need it -- then remove the following line.
        self.trans = trans
        return do_complete(self.backend, login=lambda backend, user, social_user: self.login_user(user), user=self.get_current_user(trans), state=state_token)

# TODO: find a better way to do this
_trans = None


class Strategy(BaseStrategy):

    def __init__(self, trans, storage, tpl=None):
        global _trans
        _trans = trans
        self.trans = trans
        self.request = trans.request
        self.session = trans.session if trans.session else {}
        config['SOCIAL_AUTH_REDIRECT_IS_HTTPS'] = True if self.trans.request.host.startswith('https:') else False
        super(Strategy, self).__init__(storage, tpl)

    # Settings
    def get_setting(self, name):
        """Return value for given setting name"""
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

    def disconnect(self, user, association_id=None, *args, **kwargs):
        return self.backend.disconnect(
            user=user, association_id=association_id,
            *args, **kwargs
        )

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






from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from social_core.utils import setting_name, module_member
from social_sqlalchemy.storage import SQLAlchemyUserMixin, \
                                      SQLAlchemyAssociationMixin, \
                                      SQLAlchemyNonceMixin, \
                                      SQLAlchemyCodeMixin, \
                                      SQLAlchemyPartialMixin, \
                                      BaseSQLAlchemyStorage


SocialBase = declarative_base()

UID_LENGTH = config.get(setting_name('UID_LENGTH'), 255)

from ..authnz.models import User
User = User # module_member(config[setting_name('USER_MODEL')])



# TODO: Find a better name for this.
class WebpySocialBase(object):
    @classmethod
    def _session(cls):
        return _trans.sa_session


class UserSocialAuth(WebpySocialBase, SQLAlchemyUserMixin, SocialBase):
    """Social Auth association model"""
    uid = Column(String(UID_LENGTH))
    user_id = Column(User.id.type, ForeignKey(User.id),
                     nullable=False, index=True)
    user = relationship(User, backref='social_auth')

    @classmethod
    def username_max_length(cls):
        return User.__table__.columns.get('username').type.length

    @classmethod
    def user_model(cls):
        return User


class Nonce(WebpySocialBase, SQLAlchemyNonceMixin, SocialBase):
    """One use numbers"""
    pass


class Association(WebpySocialBase, SQLAlchemyAssociationMixin, SocialBase):
    """OpenId account association"""
    pass


class Code(WebpySocialBase, SQLAlchemyCodeMixin, SocialBase):
    """Mail validation single one time use code"""
    pass


class Partial(WebpySocialBase, SQLAlchemyPartialMixin, SocialBase):
    """Partial pipeline storage"""
    pass


class Storage(BaseSQLAlchemyStorage):
    user = UserSocialAuth
    nonce = Nonce
    association = Association
    code = Code
    partial = Partial

