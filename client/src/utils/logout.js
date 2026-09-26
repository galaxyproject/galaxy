import axios from "axios";

import { getGalaxyInstance } from "@/app";
import { withPrefix } from "@/utils/redirect";
import { addSearchParams } from "@/utils/url";

function userLogoutUrl(sessionCsrfToken, logoutAll) {
    return addSearchParams(withPrefix("/user/logout"), {
        session_csrf_token: sessionCsrfToken,
        logout_all: String(logoutAll),
    });
}

function authnzLogoutUrl(provider, logoutAll) {
    const params = { logout_all: String(logoutAll) };
    if (provider) {
        params.provider = provider;
    }
    return addSearchParams(withPrefix("/authnz/logout"), params);
}

function hasAuthnzLogoutResponse(response) {
    return Boolean(response?.data?.redirect_uri || response?.data?.message);
}

/**
 * Handles user logout.  Invalidates the current session, checks to see if we
 * need to log out of OIDC too, and goes to our POST_LOGOUT_URL (or some other
 * configured redirect). */
export function userLogout(logoutAll = false) {
    const Galaxy = getGalaxyInstance();
    const post_user_logout_href = Galaxy.config.post_user_logout_href;
    const session_csrf_token = Galaxy.session_csrf_token;
    const provider = localStorage.getItem("galaxy-provider");
    const logoutRequest = Galaxy.config.enable_oidc
        ? axios.get(authnzLogoutUrl(provider, logoutAll)).then((response) => {
              if (hasAuthnzLogoutResponse(response)) {
                  return response;
              }
              return axios.get(userLogoutUrl(session_csrf_token, logoutAll));
          })
        : axios.get(userLogoutUrl(session_csrf_token, logoutAll));

    localStorage.removeItem("galaxy-provider");

    return logoutRequest.then((response) => {
        if (Galaxy.user) {
            Galaxy.user.clearSessionStorage();
        }
        if (response.data?.redirect_uri) {
            window.top.location.href = response.data.redirect_uri;
        } else {
            window.top.location.href = withPrefix(post_user_logout_href);
        }
    });
}

/** User logout with 'log out all sessions' flag set.  This will invalidate all
 * active sessions a user might have. */
export function userLogoutAll() {
    return userLogout(true);
}

/** Purely clientside logout, dumps session and redirects without invalidating
 * serverside. Currently only used when marking an account deleted -- any
 * subsequent navigation after the deletion API request would fail otherwise */
export function userLogoutClient() {
    const Galaxy = getGalaxyInstance();
    Galaxy.user?.clearSessionStorage();
    const post_user_logout_href = Galaxy.config.post_user_logout_href;
    window.top.location.href = withPrefix(post_user_logout_href);
}
