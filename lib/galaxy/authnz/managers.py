import builtins
import logging

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
from galaxy.util.resources import (
    as_file,
    resource_path,
)
from .custos_authnz import (
    CustosAuthFactory,
    KEYCLOAK_BACKENDS,
)
from .psa_authnz import (
    BACKENDS_NAME,
    PSAAuthnz,
)

OIDC_BACKEND_SCHEMA = resource_path(__name__, "xsd/oidc_backends_config.xsd")

log = logging.getLogger(__name__)

# Note: This if for backward compatibility. Icons can be specified in oidc_backends_config.xml.
DEFAULT_OIDC_IDP_ICONS = {
    "google": "https://developers.google.com/identity/images/btn_google_signin_light_normal_web.png",
    "elixir": "https://lifescience-ri.eu/fileadmin/lifescience-ri/media/Images/button-login-small.png",
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
                    f"found `{root.tag}` instead -- unable to continue."
                )
            for child in root:
                if child.tag != "Setter":
                    log.error(
                        "Expect a node with `Setter` tag, found a node with `%s` tag instead; skipping this node.",
                        child.tag,
                    )
                    continue
                if "Property" not in child.attrib or "Value" not in child.attrib or "Type" not in child.attrib:
                    log.error(
                        "Could not find the node attributes `Property` and/or `Value` and/or `Type`;"
                        f" found these attributes: `{child.attrib}`; skipping this node."
                    )
                    continue
                try:
                    if child.get("Type") == "bool":
                        func = string_as_bool
                    else:
                        func = getattr(builtins, child.get("Type"))
                except AttributeError:
                    log.error(
                        "The value of attribute `Type`, `%s`, is not a valid built-in type; skipping this node",
                        child.get("Type"),
                    )
                    continue
                self.oidc_config[child.get("Property")] = func(child.get("Value"))
        except ImportError:
            raise
        except etree.ParseError as e:
            raise etree.ParseError(f"Invalid configuration at `{config_file}`: {e} -- unable to continue.")

    def _get_idp_icon(self, idp):
        return self.oidc_backends_config[idp].get("icon") or DEFAULT_OIDC_IDP_ICONS.get(idp)

    def _get_idp_button_text(self, idp):
        return self.oidc_backends_config[idp].get("custom_button_text")

    def _parse_oidc_backends_config(self, config_file):
        self.oidc_backends_config = {}
        self.oidc_backends_implementation = {}
        try:
            with as_file(OIDC_BACKEND_SCHEMA) as oidc_backend_schema_path:
                tree = parse_xml(config_file, schemafname=oidc_backend_schema_path)
            root = tree.getroot()
            if root.tag != "OIDC":
                raise etree.ParseError(
                    "The root element in OIDC config xml file is expected to be `OIDC`, "
                    f"found `{root.tag}` instead -- unable to continue."
                )
            for child in root:
                if child.tag != "provider":
                    log.error(
                        "Expect a node with `provider` tag, found a node with `%s` tag instead; skipping the node.",
                        child.tag,
                    )
                    continue
                if "name" not in child.attrib:
                    log.error(f"Could not find a node attribute 'name'; skipping the node '{child.tag}'.")
                    continue
                idp = child.get("name").lower()
                if idp in BACKENDS_NAME:
                    self.oidc_backends_config[idp] = self._parse_idp_config(child)
                    self.oidc_backends_implementation[idp] = "psa"
                    self.app.config.oidc[idp] = {
                        "icon": self._get_idp_icon(idp),
                        "custom_button_text": self._get_idp_button_text(idp),
                    }
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
        if config_xml.find("label") is not None:
            rtv["label"] = config_xml.find("label").text
        if config_xml.find("require_create_confirmation") is not None:
            rtv["require_create_confirmation"] = asbool(config_xml.find("require_create_confirmation").text)
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
        if config_xml.find("tenant_id") is not None:
            rtv["tenant_id"] = config_xml.find("tenant_id").text
        if config_xml.find("oidc_endpoint") is not None:
            rtv["oidc_endpoint"] = config_xml.find("oidc_endpoint").text
        if config_xml.find("custom_button_text") is not None:
            rtv["custom_button_text"] = config_xml.find("custom_button_text").text
        if config_xml.find("pkce_support") is not None:
            rtv["pkce_support"] = asbool(config_xml.find("pkce_support").text)
        if config_xml.find("accepted_audiences") is not None:
            rtv["accepted_audiences"] = config_xml.find("accepted_audiences").text
        # this is a EGI Check-in specific config
        if config_xml.find("checkin_env") is not None:
            rtv["checkin_env"] = config_xml.find("checkin_env").text

        return rtv

    def _parse_custos_config(self, config_xml):
        rtv = {
            "url": config_xml.find("url").text,
            "client_id": config_xml.find("client_id").text,
            "client_secret": config_xml.find("client_secret").text,
            "redirect_uri": config_xml.find("redirect_uri").text,
            "enable_idp_logout": asbool(config_xml.findtext("enable_idp_logout", "false")),
        }
        if config_xml.find("label") is not None:
            rtv["label"] = config_xml.find("label").text
        if config_xml.find("require_create_confirmation") is not None:
            rtv["require_create_confirmation"] = asbool(config_xml.find("require_create_confirmation").text)
        if config_xml.find("credential_url") is not None:
            rtv["credential_url"] = config_xml.find("credential_url").text
        if config_xml.find("well_known_oidc_config_uri") is not None:
            rtv["well_known_oidc_config_uri"] = config_xml.find("well_known_oidc_config_uri").text
        if config_xml.findall("allowed_idp") is not None:
            self.allowed_idps = [idp.text for idp in config_xml.findall("allowed_idp")]
        if config_xml.find("ca_bundle") is not None:
            rtv["ca_bundle"] = config_xml.find("ca_bundle").text
        if config_xml.find("icon") is not None:
            rtv["icon"] = config_xml.find("icon").text
        if config_xml.find("extra_scopes") is not None:
            rtv["extra_scopes"] = listify(config_xml.find("extra_scopes").text)
        if config_xml.find("pkce_support") is not None:
            rtv["pkce_support"] = asbool(config_xml.find("pkce_support").text)
        if config_xml.find("accepted_audiences") is not None:
            rtv["accepted_audiences"] = config_xml.find("accepted_audiences").text
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
            identity_provider_class = self._get_identity_provider_factory(self.oidc_backends_implementation[provider])
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
    def _get_identity_provider_factory(implementation):
        if implementation == "psa":
            return PSAAuthnz
        elif implementation == "custos":
            return CustosAuthFactory.GetCustosBasedAuthProvider
        else:
            return None

    @staticmethod
    def can_user_assume_authn(trans, authn_id):
        qres = trans.sa_session.query(model.UserAuthnzToken).get(authn_id)
        if qres is None:
            msg = f"Authentication record with the given `authn_id` (`{trans.security.encode_id(authn_id)}`) not found."
            log.debug(msg)
            raise exceptions.ObjectNotFound(msg)
        if qres.user_id != trans.user.id:
            msg = (
                f"The request authentication with ID `{trans.security.encode_id(authn_id)}` is not accessible to user with ID "
                f"`{trans.security.encode_id(trans.user.id)}`."
            )
            log.warning(msg)
            raise exceptions.ItemAccessibilityException(msg)

    def refresh_expiring_oidc_tokens_for_provider(self, trans, auth):
        try:
            success, message, backend = self._get_authnz_backend(auth.provider)
            if success is False:
                msg = f"An error occurred when refreshing user token on `{auth.provider}` identity provider: {message}"
                log.error(msg)
                return False
            refreshed = backend.refresh(trans, auth)
            if refreshed:
                log.debug(f"Refreshed user token via `{auth.provider}` identity provider")
            return True
        except Exception:
            log.exception("An error occurred when refreshing user token")
            return False

    def refresh_expiring_oidc_tokens(self, trans, user=None):
        user = trans.user or user
        if not isinstance(user, model.User):
            return
        for auth in user.custos_auth or []:
            self.refresh_expiring_oidc_tokens_for_provider(trans, auth)
        for auth in user.social_auth or []:
            self.refresh_expiring_oidc_tokens_for_provider(trans, auth)

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

    def _assert_jwt_contains_scopes(self, user, jwt, required_scopes):
        if not jwt:
            raise exceptions.AuthenticationFailed(
                err_msg=f"User: {user.username} does not have the required scopes: [{required_scopes}]"
            )
        scopes = jwt.get("scope") or ""
        if not set(required_scopes).issubset(scopes.split(" ")):
            raise exceptions.AuthenticationFailed(
                err_msg=f"User: {user.username} has JWT with scopes: [{scopes}] but not required scopes: [{required_scopes}]"
            )

    def _validate_permissions(self, user, jwt):
        required_scopes = [f"{self.app.config.oidc_scope_prefix}:*"]
        self._assert_jwt_contains_scopes(user, jwt, required_scopes)

    def _match_access_token_to_user_in_provider(self, sa_session, provider, access_token):
        try:
            success, message, backend = self._get_authnz_backend(provider)
            if success is False:
                msg = f"An error occurred when obtaining user by token with provider `{provider}`: {message}"
                log.error(msg)
                return None
            user, jwt = None, None
            try:
                user, jwt = backend.decode_user_access_token(sa_session, access_token)
            except Exception:
                log.exception("Could not decode access token")
                raise exceptions.AuthenticationFailed(err_msg="Invalid access token or an unexpected error occurred.")
            if user and jwt:
                self._validate_permissions(user, jwt)
                return user
            elif not user and jwt:
                # jwt was decoded, but no user could be matched
                raise exceptions.AuthenticationFailed(
                    err_msg="Cannot locate user by access token. The user should log into Galaxy at least once with this OIDC provider."
                )
            # Both jwt and user are empty, which means that this provider can't process this access token
            return None
        except NotImplementedError:
            return None

    def match_access_token_to_user(self, sa_session, access_token):
        for provider in self.oidc_backends_config:
            user = self._match_access_token_to_user_in_provider(sa_session, provider, access_token)
            if user:
                return user
        return None

    def logout(self, provider, trans, post_user_logout_href=None):
        """
        Log the user out of the identity provider.

        :type provider: string
        :param provider: set the name of the identity provider.
        :type trans: GalaxyWebTransaction
        :param trans: Galaxy web transaction.
        :type post_user_logout_href: string
        :param post_user_logout_href: (Optional) URL for identity provider
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
            return True, message, backend.logout(trans, post_user_logout_href)
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
                return backend.disconnect(provider, trans, disconnect_redirect_url, email=email)
            return backend.disconnect(provider, trans, disconnect_redirect_url)
        except Exception:
            msg = f"An error occurred when disconnecting authentication with `{provider}` identity provider for user `{trans.user.username}`"
            log.exception(msg)
            return False, msg, None
