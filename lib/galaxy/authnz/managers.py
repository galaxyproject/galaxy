import builtins
import copy
import json
import logging
import os
import random
import string

import requests
from cloudauthz import CloudAuthz
from cloudauthz.exceptions import CloudAuthzBaseException

from galaxy import (
    exceptions,
    model,
)
from galaxy.util import (
    asbool,
    etree,
    listify,
    parse_xml,
    string_as_bool,
    unicodify,
)
from .custos_authnz import (
    CustosAuthnz,
    KEYCLOAK_BACKENDS,
)
from .psa_authnz import (
    BACKENDS_NAME,
    on_the_fly_config,
    PSAAuthnz,
    Storage,
    Strategy,
)

log = logging.getLogger(__name__)

# Note: This if for backward compatibility. Icons can be specified in oidc_backends_config.xml.
DEFAULT_OIDC_IDP_ICONS = {
    "google": "https://developers.google.com/identity/images/btn_google_signin_light_normal_web.png",
    "elixir": "https://elixir-europe.org/sites/default/files/images/login-button-orange.png",
    "okta": "https://www.okta.com/sites/all/themes/Okta/images/blog/Logos/Okta_Logo_BrightBlue_Medium.png",
}


class AuthnzManager:
    def __init__(self, app, oidc_config_file, oidc_backends_config_file):
        """
        :type app: galaxy.app.UniverseApplication
        :param app:

        :type config: string
        :param config: sets the path for OIDC configuration
            file (e.g., oidc_backends_config.xml).
        """
        self.app = app
        self.allowed_idps = None
        self._parse_oidc_config(oidc_config_file)
        self._parse_oidc_backends_config(oidc_backends_config_file)

    def _parse_oidc_config(self, config_file):
        self.oidc_config = {}
        try:
            tree = parse_xml(config_file)
            root = tree.getroot()
            if root.tag != "OIDC":
                raise etree.ParseError(
                    "The root element in OIDC_Config xml file is expected to be `OIDC`, "
                    "found `{}` instead -- unable to continue.".format(root.tag)
                )
            for child in root:
                if child.tag != "Setter":
                    log.error(
                        "Expect a node with `Setter` tag, found a node with `{}` tag instead; "
                        "skipping this node.".format(child.tag)
                    )
                    continue
                if "Property" not in child.attrib or "Value" not in child.attrib or "Type" not in child.attrib:
                    log.error(
                        "Could not find the node attributes `Property` and/or `Value` and/or `Type`;"
                        " found these attributes: `{}`; skipping this node.".format(child.attrib)
                    )
                    continue
                try:
                    if child.get("Type") == "bool":
                        func = string_as_bool
                    else:
                        func = getattr(builtins, child.get("Type"))
                except AttributeError:
                    log.error(
                        "The value of attribute `Type`, `{}`, is not a valid built-in type;" " skipping this node"
                    ).format(child.get("Type"))
                    continue
                self.oidc_config[child.get("Property")] = func(child.get("Value"))
        except ImportError:
            raise
        except etree.ParseError as e:
            raise etree.ParseError(f"Invalid configuration at `{config_file}`: {e} -- unable to continue.")

    def _get_idp_icon(self, idp):
        return self.oidc_backends_config[idp].get("icon") or DEFAULT_OIDC_IDP_ICONS.get(idp)

    def _parse_oidc_backends_config(self, config_file):
        self.oidc_backends_config = {}
        self.oidc_backends_implementation = {}
        try:
            tree = parse_xml(config_file)
            root = tree.getroot()
            if root.tag != "OIDC":
                raise etree.ParseError(
                    "The root element in OIDC config xml file is expected to be `OIDC`, "
                    "found `{}` instead -- unable to continue.".format(root.tag)
                )
            for child in root:
                if child.tag != "provider":
                    log.error(
                        "Expect a node with `provider` tag, found a node with `{}` tag instead; "
                        "skipping the node.".format(child.tag)
                    )
                    continue
                if "name" not in child.attrib:
                    log.error(f"Could not find a node attribute 'name'; skipping the node '{child.tag}'.")
                    continue
                idp = child.get("name").lower()
                if idp in BACKENDS_NAME:
                    self.oidc_backends_config[idp] = self._parse_idp_config(child)
                    self.oidc_backends_implementation[idp] = "psa"
                    self.app.config.oidc[idp] = {"icon": self._get_idp_icon(idp)}
                elif idp in KEYCLOAK_BACKENDS:
                    self.oidc_backends_config[idp] = self._parse_custos_config(child)
                    self.oidc_backends_implementation[idp] = "custos"
                    self.app.config.oidc[idp] = {"icon": self._get_idp_icon(idp)}
                else:
                    raise etree.ParseError("Unknown provider specified")
            if len(self.oidc_backends_config) == 0:
                raise etree.ParseError("No valid provider configuration parsed.")
        except ImportError:
            raise
        except etree.ParseError as e:
            raise etree.ParseError(f"Invalid configuration at `{config_file}`: {e} -- unable to continue.")

    def _parse_idp_config(self, config_xml):
        rtv = {
            "client_id": config_xml.find("client_id").text,
            "client_secret": config_xml.find("client_secret").text,
            "redirect_uri": config_xml.find("redirect_uri").text,
            "enable_idp_logout": asbool(config_xml.findtext("enable_idp_logout", "false")),
        }
        if config_xml.find("prompt") is not None:
            rtv["prompt"] = config_xml.find("prompt").text
        if config_xml.find("api_url") is not None:
            rtv["api_url"] = config_xml.find("api_url").text
        if config_xml.find("url") is not None:
            rtv["url"] = config_xml.find("url").text
        if config_xml.find("icon") is not None:
            rtv["icon"] = config_xml.find("icon").text
        if config_xml.find("extra_scopes") is not None:
            rtv["extra_scopes"] = listify(config_xml.find("extra_scopes").text)
        if config_xml.find("pkce_support") is not None:
            rtv["pkce_support"] = asbool(config_xml.find("pkce_support").text)

        return rtv

    def _parse_custos_config(self, config_xml):
        rtv = {
            "url": config_xml.find("url").text,
            "client_id": config_xml.find("client_id").text,
            "client_secret": config_xml.find("client_secret").text,
            "redirect_uri": config_xml.find("redirect_uri").text,
            "enable_idp_logout": asbool(config_xml.findtext("enable_idp_logout", "false")),
        }
        if config_xml.find("credential_url") is not None:
            rtv["credential_url"] = config_xml.find("credential_url").text
        if config_xml.find("well_known_oidc_config_uri") is not None:
            rtv["well_known_oidc_config_uri"] = config_xml.find("well_known_oidc_config_uri").text
        if config_xml.findall("allowed_idp") is not None:
            self.allowed_idps = list(map(lambda idp: idp.text, config_xml.findall("allowed_idp")))
        if config_xml.find("ca_bundle") is not None:
            rtv["ca_bundle"] = config_xml.find("ca_bundle").text
        if config_xml.find("icon") is not None:
            rtv["icon"] = config_xml.find("icon").text
        if config_xml.find("pkce_support") is not None:
            rtv["pkce_support"] = asbool(config_xml.find("pkce_support").text)
        return rtv

    def get_allowed_idps(self):
        # None, if no allowed idp list is set, and a list of EntityIDs if configured (in oidc_backend)
        return self.allowed_idps

    def _unify_provider_name(self, provider):
        if provider.lower() in self.oidc_backends_config:
            return provider.lower()
        for k, v in BACKENDS_NAME.items():
            if v == provider:
                return k.lower()
        return None

    def _get_authnz_backend(self, provider, idphint=None):
        unified_provider_name = self._unify_provider_name(provider)
        if unified_provider_name in self.oidc_backends_config:
            provider = unified_provider_name
            identity_provider_class = self._get_identity_provider_class(self.oidc_backends_implementation[provider])
            try:
                if provider in KEYCLOAK_BACKENDS:
                    return (
                        True,
                        "",
                        identity_provider_class(
                            unified_provider_name,
                            self.oidc_config,
                            self.oidc_backends_config[unified_provider_name],
                            idphint=idphint,
                        ),
                    )
                else:
                    return (
                        True,
                        "",
                        identity_provider_class(
                            unified_provider_name, self.oidc_config, self.oidc_backends_config[unified_provider_name]
                        ),
                    )
            except Exception as e:
                log.exception(f"An error occurred when loading {identity_provider_class.__name__}")
                return False, unicodify(e), None
        else:
            msg = f"The requested identity provider, `{provider}`, is not a recognized/expected provider."
            log.debug(msg)
            return False, msg, None

    @staticmethod
    def _get_identity_provider_class(implementation):
        if implementation == "psa":
            return PSAAuthnz
        elif implementation == "custos":
            return CustosAuthnz
        else:
            return None

    def _extend_cloudauthz_config(self, cloudauthz, request, sa_session, user_id):
        config = copy.deepcopy(cloudauthz.config)
        if cloudauthz.provider == "aws":
            success, message, backend = self._get_authnz_backend(cloudauthz.authn.provider)
            strategy = Strategy(request, None, Storage, backend.config)
            on_the_fly_config(sa_session)
            try:
                config["id_token"] = cloudauthz.authn.get_id_token(strategy)
            except requests.exceptions.HTTPError as e:
                msg = (
                    "Sign-out from Galaxy and remove its access from `{}`, then log back in using `{}` "
                    "account.".format(self._unify_provider_name(cloudauthz.authn.provider), cloudauthz.authn.uid)
                )
                log.debug(
                    "Failed to get/refresh ID token for user with ID `{}` for assuming authz_id `{}`. "
                    "User may not have a refresh token. If the problem persists, set the `prompt` key to "
                    "`consent` in `oidc_backends_config.xml`, then restart Galaxy and ask user to: {}"
                    "Error Message: `{}`".format(user_id, cloudauthz.id, msg, e.response.text)
                )
                raise exceptions.AuthenticationFailed(
                    err_msg="An error occurred getting your ID token. {}. If the problem persists, please "
                    "contact Galaxy admin.".format(msg)
                )
        return config

    @staticmethod
    def can_user_assume_authn(trans, authn_id):
        qres = trans.sa_session.query(model.UserAuthnzToken).get(authn_id)
        if qres is None:
            msg = "Authentication record with the given `authn_id` (`{}`) not found.".format(
                trans.security.encode_id(authn_id)
            )
            log.debug(msg)
            raise exceptions.ObjectNotFound(msg)
        if qres.user_id != trans.user.id:
            msg = "The request authentication with ID `{}` is not accessible to user with ID " "`{}`.".format(
                trans.security.encode_id(authn_id), trans.security.encode_id(trans.user.id)
            )
            log.warning(msg)
            raise exceptions.ItemAccessibilityException(msg)

    @staticmethod
    def try_get_authz_config(sa_session, user_id, authz_id):
        """
        It returns a cloudauthz config (see model.CloudAuthz) with the
        given ID; and raise an exception if either a config with given
        ID does not exist, or the configuration is defined for a another
        user than trans.user.

        :type  trans:       galaxy.webapps.base.webapp.GalaxyWebTransaction
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
            msg = (
                "The request authorization configuration (with ID:`{}`) is not accessible for user with "
                "ID:`{}`.".format(qres.id, user_id)
            )
            log.warning(msg)
            raise exceptions.ItemAccessibilityException(msg)
        return qres

    def authenticate(self, provider, trans, idphint=None):
        """
        :type provider: string
        :param provider: set the name of the identity provider to be
            used for authentication flow.
        :type trans: GalaxyWebTransaction
        :param trans: Galaxy web transaction.
        :return: an identity provider specific authentication redirect URI.
        """
        try:
            success, message, backend = self._get_authnz_backend(provider, idphint=idphint)
            if success is False:
                return False, message, None
            elif provider in KEYCLOAK_BACKENDS:
                if self.allowed_idps and (idphint not in self.allowed_idps):
                    msg = f"An error occurred when authenticating a user. Invalid EntityID: `{idphint}`"
                    log.exception(msg)
                    return False, msg, None
                return (
                    True,
                    f"Redirecting to the `{provider}` identity provider for authentication",
                    backend.authenticate(trans, idphint),
                )
            return (
                True,
                f"Redirecting to the `{provider}` identity provider for authentication",
                backend.authenticate(trans),
            )
        except Exception:
            msg = f"An error occurred when authenticating a user on `{provider}` identity provider"
            log.exception(msg)
            return False, msg, None

    def callback(self, provider, state_token, authz_code, trans, login_redirect_url, idphint=None):
        try:
            success, message, backend = self._get_authnz_backend(provider, idphint=idphint)
            if success is False:
                return False, message, (None, None)
            return success, message, backend.callback(state_token, authz_code, trans, login_redirect_url)
        except exceptions.AuthenticationFailed:
            raise
        except Exception:
            msg = f"An error occurred when handling callback from `{provider}` identity provider.  Please contact an administrator for assistance."
            log.exception(msg)
            return False, msg, (None, None)

    def create_user(self, provider, token, trans, login_redirect_url):
        try:
            success, message, backend = self._get_authnz_backend(provider)
            if success is False:
                return False, message, (None, None)
            return success, message, backend.create_user(token, trans, login_redirect_url)
        except exceptions.AuthenticationFailed:
            log.exception("Error creating user")
            raise
        except Exception:
            msg = f"An error occurred when creating a user with `{provider}` identity provider.  Please contact an administrator for assistance."
            log.exception(msg)
            return False, msg, (None, None)

    def logout(self, provider, trans, post_logout_redirect_url=None):
        """
        Log the user out of the identity provider.

        :type provider: string
        :param provider: set the name of the identity provider.
        :type trans: GalaxyWebTransaction
        :param trans: Galaxy web transaction.
        :type post_logout_redirect_url: string
        :param post_logout_redirect_url: (Optional) URL for identity provider
            to redirect to after logging user out.
        :return: a tuple (success boolean, message, redirect URI)
        """
        try:
            # check if logout is enabled for this idp and return false if not
            unified_provider_name = self._unify_provider_name(provider)
            if self.oidc_backends_config[unified_provider_name]["enable_idp_logout"] is False:
                return False, f"IDP logout is not enabled for {provider}", None

            success, message, backend = self._get_authnz_backend(provider)
            if success is False:
                return False, message, None
            return True, message, backend.logout(trans, post_logout_redirect_url)
        except Exception:
            msg = f"An error occurred when logging out from `{provider}` identity provider.  Please contact an administrator for assistance."
            log.exception(msg)
            return False, msg, None

    def disconnect(self, provider, trans, email=None, disconnect_redirect_url=None, idphint=None):
        try:
            success, message, backend = self._get_authnz_backend(provider, idphint=idphint)
            if success is False:
                return False, message, None
            elif provider in KEYCLOAK_BACKENDS:
                return backend.disconnect(provider, trans, email, disconnect_redirect_url)
            return backend.disconnect(provider, trans, disconnect_redirect_url)
        except Exception:
            msg = (
                "An error occurred when disconnecting authentication with `{}` identity provider for user `{}`".format(
                    provider, trans.user.username
                )
            )
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
            log.info(
                "Requesting credentials using CloudAuthz with config id `{}` on be half of user `{}`.".format(
                    cloudauthz.id, user_id
                )
            )
            credentials = ca.authorize(cloudauthz.provider, config)
            return credentials
        except CloudAuthzBaseException as e:
            log.info(e)
            raise exceptions.AuthenticationFailed(e)
        except NotImplementedError as e:
            log.info(e)
            raise exceptions.RequestParameterInvalidException(e)

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
        filename = os.path.abspath(
            os.path.join(
                new_file_path,
                "cd_"
                + "".join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(11)),
            )
        )
        credentials = self.get_cloud_access_credentials(cloudauthz, sa_session, user_id, request)
        log.info(
            "Writting credentials generated using CloudAuthz with config id `{}` to the following file: `{}`"
            "".format(cloudauthz.id, filename)
        )
        with open(filename, "w") as f:
            f.write(json.dumps(credentials))
        return filename
