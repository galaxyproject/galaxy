
from cloudauthz import CloudAuthz
import importlib
import logging
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

from .psa_authnz import PSAAuthnz

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
            raise ParseError("Invalid configuration at `{}`: {} -- unable to continue.".format(config_file, e.message))

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
            raise ParseError("Invalid configuration at `{}`: {} -- unable to continue.".format(config_file, e.message))
        # except Exception as e:
        #     raise Exception("Malformed OIDC Configuration XML -- unable to continue. {}".format(e.message))

    def _parse_google_config(self, config_xml):
        rtv = {
            'client_id': config_xml.find('client_id').text,
            'client_secret': config_xml.find('client_secret').text,
            'redirect_uri': config_xml.find('redirect_uri').text}
        if config_xml.find('prompt') is not None:
            rtv['prompt'] = config_xml.find('prompt').text
        return rtv

    def _get_authnz_backend(self, provider):
        provider = provider.lower()
        if provider in self.oidc_backends_config:
            try:
                return True, "", PSAAuthnz(provider, self.oidc_config, self.oidc_backends_config[provider])
            except Exception as e:
                log.exception('An error occurred when loading PSAAuthnz: ', str(e))
                return False, str(e), None
        else:
            msg = 'The requested identity provider, `{}`, is not a recognized/expected provider'.format(provider)
            log.debug(msg)
            return False, msg, None

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
        except Exception as e:
            msg = 'An error occurred when authenticating a user on `{}` identity provider: {}'.format(provider, str(e))
            log.exception(msg)
            return False, msg, None

    def callback(self, provider, state_token, authz_code, trans, login_redirect_url):
        try:
            success, message, backend = self._get_authnz_backend(provider)
            if success is False:
                return False, message, (None, None)
            return True, message, backend.callback(state_token, authz_code, trans, login_redirect_url)
        except Exception as e:
            msg = 'An error occurred when handling callback from `{}` identity provider; {}'.format(provider, str(e))
            log.exception(msg)
            return False, msg, (None, None)

    def disconnect(self, provider, trans, disconnect_redirect_url=None):
        try:
            success, message, backend = self._get_authnz_backend(provider)
            if success is False:
                return False, message, None
            return backend.disconnect(provider, trans, disconnect_redirect_url)
        except Exception as e:
            msg = 'An error occurred when disconnecting authentication with `{}` identity provider for user `{}`; ' \
                  '{}'.format(provider, trans.user.username, str(e))
            log.exception(msg)
            return False, msg, None

    @staticmethod
    def get_cloud_access_credentials(cloudauthz):
        """

        :param cloudauthz:
        :return:
        """
        config = cloudauthz.config
        config['id_token'] = cloudauthz.authn.get_id_token()
        ca = CloudAuthz()
        return ca.authorize(cloudauthz.provider, config)
