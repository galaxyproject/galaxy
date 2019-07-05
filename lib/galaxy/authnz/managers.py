
import copy
import importlib
import json
import logging
import os
import random
import string
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

import requests
from cloudauthz import CloudAuthz
from cloudauthz.exceptions import (
    CloudAuthzBaseException
)

from galaxy import exceptions
from galaxy import model
from .psa_authnz import (
    BACKENDS_NAME,
    on_the_fly_config,
    PSAAuthnz,
    Storage,
    Strategy
)

log = logging.getLogger(__name__)


class AuthnzManager(object):

    def __init__(self, app, oidc_config_file, oidc_backends_config_file):
        """
        :type app: galaxy.app.UniverseApplication
        :param app:

        :type config: string
        :param config: sets the path for OIDC configuration
            file (e.g., oidc_backends_config.xml).
        """
        self._parse_oidc_config(oidc_config_file)
        self._parse_oidc_backends_config(oidc_backends_config_file)

    def _parse_oidc_config(self, config_file):
        self.oidc_config = {}
        try:
            tree = ET.parse(config_file)
            root = tree.getroot()
            if root.tag != 'OIDC':
                raise ParseError("The root element in OIDC_Config xml file is expected to be `OIDC`, "
                                 "found `{}` instead -- unable to continue.".format(root.tag))
            for child in root:
                if child.tag != 'Setter':
                    log.error("Expect a node with `Setter` tag, found a node with `{}` tag instead; "
                              "skipping this node.".format(child.tag))
                    continue
                if 'Property' not in child.attrib or 'Value' not in child.attrib or 'Type' not in child.attrib:
                    log.error("Could not find the node attributes `Property` and/or `Value` and/or `Type`;"
                              " found these attributes: `{}`; skipping this node.".format(child.attrib))
                    continue
                try:
                    func = getattr(importlib.import_module('__builtin__'), child.get('Type'))
                except AttributeError:
                    log.error("The value of attribute `Type`, `{}`, is not a valid built-in type;"
                              " skipping this node").format(child.get('Type'))
                    continue
                self.oidc_config[child.get('Property')] = func(child.get('Value'))
        except ImportError:
            raise
        except ParseError as e:
            raise ParseError("Invalid configuration at `{}`: {} -- unable to continue.".format(config_file, e))

    def _parse_oidc_backends_config(self, config_file):
        self.oidc_backends_config = {}
        try:
            tree = ET.parse(config_file)
            root = tree.getroot()
            if root.tag != 'OIDC':
                raise ParseError("The root element in OIDC config xml file is expected to be `OIDC`, "
                                 "found `{}` instead -- unable to continue.".format(root.tag))
            for child in root:
                if child.tag != 'provider':
                    log.error("Expect a node with `provider` tag, found a node with `{}` tag instead; "
                              "skipping the node.".format(child.tag))
                    continue
                if 'name' not in child.attrib:
                    log.error("Could not find a node attribute 'name'; skipping the node '{}'.".format(child.tag))
                    continue
                idp = child.get('name').lower()
                if idp == 'google':
                    self.oidc_backends_config[idp] = self._parse_google_config(child)
            if len(self.oidc_backends_config) == 0:
                raise ParseError("No valid provider configuration parsed.")
        except ImportError:
            raise
        except ParseError as e:
            raise ParseError("Invalid configuration at `{}`: {} -- unable to continue.".format(config_file, e))

    def _parse_google_config(self, config_xml):
        rtv = {
            'client_id': config_xml.find('client_id').text,
            'client_secret': config_xml.find('client_secret').text,
            'redirect_uri': config_xml.find('redirect_uri').text}
        if config_xml.find('prompt') is not None:
            rtv['prompt'] = config_xml.find('prompt').text
        return rtv

    def _unify_provider_name(self, provider):
        if provider.lower() in self.oidc_backends_config:
            return provider.lower()
        for k, v in BACKENDS_NAME.iteritems():
            if v == provider:
                return k.lower()

    def _get_authnz_backend(self, provider):
        provider = self._unify_provider_name(provider)
        if provider in self.oidc_backends_config:
            try:
                return True, "", PSAAuthnz(provider, self.oidc_config, self.oidc_backends_config[provider])
            except Exception as e:
                log.exception('An error occurred when loading PSAAuthnz')
                return False, str(e), None
        else:
            msg = 'The requested identity provider, `{}`, is not a recognized/expected provider'.format(provider)
            log.debug(msg)
            return False, msg, None

    def _extend_cloudauthz_config(self, cloudauthz, request, sa_session, user_id):
        config = copy.deepcopy(cloudauthz.config)
        if cloudauthz.provider == "aws":
            success, message, backend = self._get_authnz_backend(cloudauthz.authn.provider)
            strategy = Strategy(request, None, Storage, backend.config)
            on_the_fly_config(sa_session)
            try:
                config['id_token'] = cloudauthz.authn.get_id_token(strategy)
            except requests.exceptions.HTTPError as e:
                msg = "Sign-out from Galaxy and remove its access from `{}`, then log back in using `{}` " \
                      "account.".format(self._unify_provider_name(cloudauthz.authn.provider), cloudauthz.authn.uid)
                log.debug("Failed to get/refresh ID token for user with ID `{}` for assuming authz_id `{}`. "
                          "User may not have a refresh token. If the problem persists, set the `prompt` key to "
                          "`consent` in `oidc_backends_config.xml`, then restart Galaxy and ask user to: {}"
                          "Error Message: `{}`".format(user_id, cloudauthz.id, msg, e.response.text))
                raise exceptions.AuthenticationFailed(
                    err_msg="An error occurred getting your ID token. {}. If the problem persists, please "
                            "contact Galaxy admin.".format(msg))
        return config

    @staticmethod
    def can_user_assume_authn(trans, authn_id):
        qres = trans.sa_session.query(model.UserAuthnzToken).get(authn_id)
        if qres is None:
            msg = "Authentication record with the given `authn_id` (`{}`) not found.".format(
                trans.security.encode_id(authn_id))
            log.debug(msg)
            raise exceptions.ObjectNotFound(msg)
        if qres.user_id != trans.user.id:
            msg = "The request authentication with ID `{}` is not accessible to user with ID " \
                  "`{}`.".format(trans.security.encode_id(authn_id), trans.security.encode_id(trans.user.id))
            log.warn(msg)
            raise exceptions.ItemAccessibilityException(msg)

    @staticmethod
    def try_get_authz_config(sa_session, user_id, authz_id):
        """
        It returns a cloudauthz config (see model.CloudAuthz) with the
        given ID; and raise an exception if either a config with given
        ID does not exist, or the configuration is defined for a another
        user than trans.user.

        :type  trans:       galaxy.web.framework.webapp.GalaxyWebTransaction
        :param trans:       Galaxy web transaction

        :type  authz_id:    int
        :param authz_id:    The ID of a CloudAuthz configuration to be used for
                            getting temporary credentials.

        :rtype :            model.CloudAuthz
        :return:            a cloudauthz configuration.
        """
        qres = sa_session.query(model.CloudAuthz).get(authz_id)
        if qres is None:
            raise exceptions.ObjectNotFound("An authorization configuration with given ID not found.")
        if user_id != qres.user_id:
            msg = "The request authorization configuration (with ID:`{}`) is not accessible for user with " \
                  "ID:`{}`.".format(qres.id, user_id)
            log.warn(msg)
            raise exceptions.ItemAccessibilityException(msg)
        return qres

    def authenticate(self, provider, trans):
        """
        :type provider: string
        :param provider: set the name of the identity provider to be
            used for authentication flow.
        :type trans: GalaxyWebTransaction
        :param trans: Galaxy web transaction.
        :return: an identity provider specific authentication redirect URI.
        """
        try:
            success, message, backend = self._get_authnz_backend(provider)
            if success is False:
                return False, message, None
            return True, "Redirecting to the `{}` identity provider for authentication".format(provider), backend.authenticate(trans)
        except Exception:
            msg = 'An error occurred when authenticating a user on `{}` identity provider'.format(provider)
            log.exception(msg)
            return False, msg, None

    def callback(self, provider, state_token, authz_code, trans, login_redirect_url):
        try:
            success, message, backend = self._get_authnz_backend(provider)
            if success is False:
                return False, message, (None, None)
            return True, message, backend.callback(state_token, authz_code, trans, login_redirect_url)
        except Exception:
            msg = 'An error occurred when handling callback from `{}` identity provider'.format(provider)
            log.exception(msg)
            return False, msg, (None, None)

    def disconnect(self, provider, trans, disconnect_redirect_url=None):
        try:
            success, message, backend = self._get_authnz_backend(provider)
            if success is False:
                return False, message, None
            return backend.disconnect(provider, trans, disconnect_redirect_url)
        except Exception:
            msg = 'An error occurred when disconnecting authentication with `{}` identity provider for user `{}`' \
                  .format(provider, trans.user.username)
            log.exception(msg)
            return False, msg, None

    def get_cloud_access_credentials(self, cloudauthz, sa_session, user_id, request=None):
        """
        This method leverages CloudAuthz (https://github.com/galaxyproject/cloudauthz)
        to request a cloud-based resource provider (e.g., Amazon AWS, Microsoft Azure)
        for temporary access credentials to a given resource.

        It first checks if a cloudauthz config with the given ID (`authz_id`) is
        available and can be assumed by the user, and raises an exception if either
        is false. Otherwise, it then extends the cloudauthz configuration as required
        by the CloudAuthz library for the provider specified in the configuration.
        For instance, it adds on-the-fly values such as a valid OpenID Connect
        identity token, as required by CloudAuthz for AWS. Then requests temporary
        credentials from the CloudAuthz library using the updated configuration.

        :type  cloudauthz:  CloudAuthz
        :param cloudauthz:  an instance of CloudAuthz to be used for getting temporary
                            credentials.

        :type   sa_session: sqlalchemy.orm.scoping.scoped_session
        :param  sa_session: SQLAlchemy database handle.

        :type   user_id:    int
        :param  user_id:    Decoded Galaxy user ID.

        :type   request:    galaxy.web.framework.base.Request
        :param  request:    Encapsulated HTTP(S) request.

        :rtype:             dict
        :return:            a dictionary containing credentials to access a cloud-based
                            resource provider. See CloudAuthz (https://github.com/galaxyproject/cloudauthz)
                            for details on the content of this dictionary.
        """
        config = self._extend_cloudauthz_config(cloudauthz, request, sa_session, user_id)
        try:
            ca = CloudAuthz()
            log.info("Requesting credentials using CloudAuthz with config id `{}` on be half of user `{}`.".format(
                cloudauthz.id, user_id))
            return ca.authorize(cloudauthz.provider, config)
        except CloudAuthzBaseException as e:
            log.info(e)
            raise exceptions.AuthenticationFailed(e)

    def get_cloud_access_credentials_in_file(self, new_file_path, cloudauthz, sa_session, user_id, request=None):
        """
        This method leverages CloudAuthz (https://github.com/galaxyproject/cloudauthz)
        to request a cloud-based resource provider (e.g., Amazon AWS, Microsoft Azure)
        for temporary access credentials to a given resource.

        This method uses the `get_cloud_access_credentials` method to obtain temporary
        credentials, and persists them to a (temporary) file, and returns the file path.

        :type  new_file_path:   str
        :param new_file_path:   Where dataset files are saved on temporary storage.
                                See `app.config.new_file_path`.

        :type  cloudauthz:      CloudAuthz
        :param cloudauthz:      an instance of CloudAuthz to be used for getting temporary
                                credentials.

        :type  sa_session:      sqlalchemy.orm.scoping.scoped_session
        :param sa_session:      SQLAlchemy database handle.

        :type  user_id:         int
        :param user_id:         Decoded Galaxy user ID.

        :type  request:         galaxy.web.framework.base.Request
        :param request:         [Optional] Encapsulated HTTP(S) request.

        :rtype:                 str
        :return:                The filename to which credentials are written.
        """
        filename = os.path.abspath(os.path.join(new_file_path,
                                                "cd_" + ''.join(random.SystemRandom().choice(
                                                    string.ascii_uppercase + string.digits) for _ in range(11))))
        credentials = self.get_cloud_access_credentials(cloudauthz, sa_session, user_id, request)
        log.info("Writting credentials generated using CloudAuthz with config id `{}` to the following file: `{}`"
                 "".format(cloudauthz.id, filename))
        with open(filename, "w") as f:
            f.write(json.dumps(credentials))
        return filename
