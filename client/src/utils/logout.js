import axios from "axios";

const POST_LOGOUT_URL = "root/login?is_logout_redirect=true";

/**
 * Handles user logout.  Invalidates the current session, checks to see if we
 * need to log out of OIDC too, and goes to our POST_LOGOUT_URL (or some other
 * configured redirect). */
export function userLogout(logoutAll = false) {
    const galaxy = getGalaxyInstance();
    const session_csrf_token = galaxy.session_csrf_token;
    const url = `${galaxy.root}user/logout?session_csrf_token=${session_csrf_token}&logout_all=${logoutAll}`;
    axios
        .get(url)
        .then((response) => {
            if (galaxy.user) {
                galaxy.user.clearSessionStorage();
            }
            // Check if we need to logout of OIDC IDP
            if (galaxy.config.enable_oidc) {
                const provider = localStorage.getItem("galaxy-provider");
                if (provider) {
                    localStorage.removeItem("galaxy-provider");
                    return axios.get(`${galaxy.root}authnz/logout?provider=${provider}`);
                }
                return axios.get(`${galaxy.root}authnz/logout`);
            } else {
                // Otherwise pass through the initial logout response
                return response;
            }
        })
        .then((response) => {
            if (response.data?.redirect_uri) {
                window.top.location.href = response.data.redirect_uri;
            } else {
                window.top.location.href = `${galaxy.root}${POST_LOGOUT_URL}`;
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
    const galaxy = getGalaxyInstance();
    galaxy.user?.clearSessionStorage();
    window.top.location.href = `${galaxy.root}${POST_LOGOUT_URL}`;
}
