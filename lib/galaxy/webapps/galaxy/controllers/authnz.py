"""
OAuth 2.0 and OpenID Connect Authentication and Authorization Controller.
"""

import json
import logging
from datetime import (
    datetime,
    timezone,
)

import jwt

from galaxy import (
    exceptions,
    web,
)
from galaxy.util import url_get
from galaxy.web import url_for
from galaxy.webapps.base.controller import JSAppLauncher

log = logging.getLogger(__name__)

PROVIDER_COOKIE_NAME = "galaxy-oidc-provider"


class OIDC(JSAppLauncher):
    @web.json
    @web.expose
    @web.require_login("list third-party identities")
    def index(self, trans, **kwargs):
        """
        GET /authnz/
            returns a list of third-party identities associated with the user.

        :type  trans: galaxy.webapps.base.webapp.GalaxyWebTransaction
        :param trans: Galaxy web transaction.

        :param kwargs: empty dict

        :rtype: list of dicts
        :return: a list of third-party identities associated with the user account.
        """
        rtv = []
        for authnz in trans.user.social_auth:
            rtv.append(
                {"id": trans.app.security.encode_id(authnz.id), "provider": authnz.provider, "email": authnz.uid}
            )
        # Add cilogon and custos identities
        for token in trans.user.custos_auth:
            # for purely displaying the info to user, we bypass verification of
            # signature, audience, and expiration as that's potentially useful
            # information to share with the end user
            try:
                userinfo = jwt.decode(
                    token.id_token, options={"verify_signature": False, "verify_aud": False, "verify_exp": False}
                )
                rtv.append(
                    {
                        "id": trans.app.security.encode_id(token.id),
                        "provider": token.provider,
                        "email": userinfo["email"],
                        "expiration": str(datetime.fromtimestamp(userinfo["exp"], timezone.utc)),
                    }
                )
            except Exception:
                rtv.append(
                    {
                        "id": trans.app.security.encode_id(token.id),
                        "provider": token.provider,
                        "error": "Unable to decode token",
                    }
                )
        return rtv

    @web.json
    @web.expose
    def login(self, trans, provider, idphint=None):
        if not trans.app.config.enable_oidc:
            msg = "Login to Galaxy using third-party identities is not enabled on this Galaxy instance."
            log.debug(msg)
            return trans.show_error_message(msg)
        success, message, redirect_uri = trans.app.authnz_manager.authenticate(provider, trans, idphint=idphint)
        if success:
            return {"redirect_uri": redirect_uri}
        else:
            raise exceptions.AuthenticationFailed(message)

    @web.expose
    def callback(self, trans, provider, idphint=None, **kwargs):
        user = trans.user.username if trans.user is not None else "anonymous"
        if not bool(kwargs):
            log.error(f"OIDC callback received no data for provider `{provider}` and user `{user}`")
            return trans.show_error_message(
                f"Did not receive any information from the `{provider}` identity provider to complete user `{user}` authentication "
                "flow. Please try again, and if the problem persists, contact the Galaxy instance admin. Also note "
                "that this endpoint is to receive authentication callbacks only, and should not be called/reached by "
                "a user."
            )
        if "error" in kwargs:
            log.error(
                "Error handling authentication callback from `{}` identity provider for user `{}` login request."
                " Error message: {}".format(provider, user, kwargs.get("error", "None"))
            )
            return trans.show_error_message(
                f"Failed to handle authentication callback from {provider}. "
                "Please try again, and if the problem persists, contact "
                "the Galaxy instance admin"
            )
        try:
            success, message, (redirect_url, user) = trans.app.authnz_manager.callback(
                provider,
                kwargs.get("state", " "),
                kwargs["code"],
                trans,
                login_redirect_url=url_for("/"),
                idphint=idphint,
            )
        except exceptions.AuthenticationFailed:
            raise
        if success is False:
            return trans.show_error_message(message)
        if "?confirm" in redirect_url:
            return trans.response.send_redirect(url_for(redirect_url))
        if "?connect_external_provider" in redirect_url:
            return trans.response.send_redirect(url_for(redirect_url))
        elif redirect_url is None:
            redirect_url = url_for("/")

        user = user if user is not None else trans.user
        if user is None:
            return trans.show_error_message(
                f"An unknown error occurred when handling the callback from `{provider}` "
                "identity provider. Please try again, and if the problem persists, "
                "contact the Galaxy instance admin."
            )
        trans.handle_user_login(user)
        # Record which idp provider was logged into, so we can logout of it later
        trans.set_cookie(value=provider, name=PROVIDER_COOKIE_NAME)
        return trans.response.send_redirect(url_for(redirect_url))

    @web.expose
    def create_user(self, trans, provider, **kwargs):
        try:
            success, message, (redirect_url, user) = trans.app.authnz_manager.create_user(
                provider, token=kwargs.get("token", " "), trans=trans, login_redirect_url=url_for("/")
            )
        except exceptions.AuthenticationFailed as e:
            return trans.response.send_redirect(
                f"{trans.request.url_path + url_for('/')}root/login?message={str(e) or 'Duplicate Email'}"
            )

        if success is False:
            return trans.show_error_message(message)
        user = user if user is not None else trans.user
        if user is None:
            return trans.show_error_message(
                f"An unknown error occurred when handling the callback from `{provider}` "
                "identity provider. Please try again, and if the problem persists, "
                "contact the Galaxy instance admin."
            )
        trans.handle_user_login(user)
        # Record which idp provider was logged into, so we can logout of it later
        trans.set_cookie(value=provider, name=PROVIDER_COOKIE_NAME)
        if redirect_url is None:
            redirect_url = url_for("/")
        return trans.response.send_redirect(url_for(redirect_url))

    @web.expose
    @web.require_login("authenticate against the selected identity provider")
    def disconnect(self, trans, provider, email=None, **kwargs):
        if trans.user is None:
            # Only logged in users are allowed here.
            return
        success, message, redirect_url = trans.app.authnz_manager.disconnect(
            provider, trans, email, disconnect_redirect_url=url_for("/")
        )
        if success is False:
            return trans.show_error_message(message)
        if redirect_url is None:
            redirect_url = url_for("/")
        return trans.response.send_redirect(redirect_url)

    @web.json
    @web.expose
    def logout(self, trans, provider, **kwargs):
        post_user_logout_href = trans.app.config.post_user_logout_href
        if post_user_logout_href is not None:
            post_user_logout_href = trans.request.base + url_for(post_user_logout_href)
        success, message, redirect_uri = trans.app.authnz_manager.logout(
            provider, trans, post_user_logout_href=post_user_logout_href
        )
        trans.handle_user_logout()
        if success:
            return {"redirect_uri": redirect_uri}
        else:
            return {"message": message}

    @web.expose
    def get_logout_url(self, trans, provider=None, **kwargs):
        idp_provider = provider if provider else trans.get_cookie(name=PROVIDER_COOKIE_NAME)
        if idp_provider:
            return trans.response.send_redirect(url_for(controller="authnz", action="logout", provider=idp_provider))

    @web.expose
    @web.json
    def get_cilogon_idps(self, trans, **kwargs):
        try:
            cilogon_idps = json.loads(url_get("https://cilogon.org/idplist/", params=dict(kwargs)))
        except Exception as e:
            raise Exception(f"Invalid server response. {str(e)}.")

        if allowed_idps := trans.app.authnz_manager.get_allowed_idps():
            validated_idps = list(filter(lambda idp: idp["EntityID"] in allowed_idps, cilogon_idps))

            if not (len(validated_idps) == len(allowed_idps)):
                validated_entity_ids = [entity["EntityID"] for entity in validated_idps]

                for idp in allowed_idps:
                    if idp not in validated_entity_ids:
                        log.debug(
                            "Invalid EntityID entered: %s. Use https://cilogon.org/idplist/ to find desired institution's EntityID.",
                            idp,
                        )

            return validated_idps
        else:
            return cilogon_idps
