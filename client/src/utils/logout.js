import axios from "axios";
import { getGalaxyInstance } from "app";
import { withPrefix } from "utils/redirect";

/**
 * Handles user logout.  Invalidates the current session, checks to see if we
 * need to log out of OIDC too, and goes to our POST_LOGOUT_URL (or some other
 * configured redirect). */
export function userLogout(logoutAll = false) {
    const Galaxy = getGalaxyInstance();
    const post_user_logout_href = Galaxy.config.post_user_logout_href;
    const session_csrf_token = Galaxy.session_csrf_token;
    const url = `/user/logout?session_csrf_token=${session_csrf_token}&logout_all=${logoutAll}`;
    axios
        .get(withPrefix(url))
        .then((response) => {
            if (Galaxy.user) {
                Galaxy.user.clearSessionStorage();
            }
            // Check if we need to logout of OIDC IDP
            if (Galaxy.config.enable_oidc) {
                const provider = localStorage.getItem("galaxy-provider");
                if (provider) {
                    localStorage.removeItem("galaxy-provider");
                    return axios.get(withPrefix(`/authnz/logout?provider=${provider}`));
                }
                return axios.get(withPrefix("/authnz/logout"));
            } else {
                // Otherwise pass through the initial logout response
                return response;
            }
        })
        .then((response) => {
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
