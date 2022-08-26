import axios from "axios";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import { MASTHEAD_TAB_ID } from "./masthead";

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

export function fetchMenu(config, mastheadOptions) {
    const Galaxy = getGalaxyInstance();
    const menu = [];
    //
    // Analyze data tab.
    //
    menu.push({
        id: MASTHEAD_TAB_ID.ANALYSIS,
        url: "",
        tooltip: _l("Tools and Current History"),
        icon: "fa-home",
    });

    //
    // Workflow tab.
    //
    menu.push({
        id: MASTHEAD_TAB_ID.WORKFLOW,
        title: _l("Workflow"),
        tooltip: _l("Chain tools into workflows"),
        disabled: !Galaxy.user.id,
        url: "workflows/list",
        target: "__use_router__",
    });

    //
    // Visualization tab.
    //
    if (mastheadOptions.enableVisualizations) {
        menu.push({
            id: MASTHEAD_TAB_ID.VISUALIZATION,
            title: _l("Visualize"),
            tooltip: _l("Visualize datasets"),
            disabled: !Galaxy.user.id,
            url: "visualizations",
            target: "__use_router__",
        });
    }

    //
    // 'Shared Items' or Libraries tab.
    //
    if (config.single_user) {
        // Single user can still use libraries, especially as we may grow that
        // functionality as a representation for external data.  The rest is
        // hidden though.
        menu.push({
            title: _l("Data Libraries"),
            url: "libraries",
            id: MASTHEAD_TAB_ID.SHARED,
        });
    } else {
        menu.push({
            id: MASTHEAD_TAB_ID.SHARED,
            title: _l("Shared Data"),
            url: "javascript:void(0)",
            tooltip: _l("Access published resources"),
            menu: [
                {
                    title: _l("Data Libraries"),
                    url: "libraries",
                },
                {
                    title: _l("Histories"),
                    url: "histories/list_published",
                    target: "__use_router__",
                },
                {
                    title: _l("Workflows"),
                    url: "workflows/list_published",
                    target: "__use_router__",
                },
                {
                    title: _l("Visualizations"),
                    url: "visualizations/list_published",
                    target: "__use_router__",
                },
                {
                    title: _l("Pages"),
                    url: "pages/list_published",
                    target: "__use_router__",
                },
            ],
        });
    }

    //
    // Admin.
    //
    if (mastheadOptions.enableAdmin) {
        menu.push({
            id: MASTHEAD_TAB_ID.ADMIN,
            title: _l("Admin"),
            url: "admin",
            tooltip: _l("Administer this Galaxy"),
            cls: "admin-only",
        });
    }

    //
    // Help tab.
    //
    const helpTab = {
        id: MASTHEAD_TAB_ID.HELP,
        title: _l("Help"),
        url: "javascript:void(0)",
        tooltip: _l("Support, contact, and community"),
        menu: [
            {
                title: _l("Galaxy Help"),
                url: config.helpsite_url,
                target: "_blank",
                hidden: !config.helpsite_url,
            },
            {
                title: _l("Support"),
                url: config.support_url,
                target: "_blank",
                hidden: !config.support_url,
            },
            {
                title: _l("Videos"),
                url: config.screencasts_url,
                target: "_blank",
                hidden: !config.screencasts_url,
            },
            {
                title: _l("Community Hub"),
                url: config.wiki_url,
                target: "_blank",
                hidden: !config.wiki_url,
            },
            {
                title: _l("How to Cite Galaxy"),
                url: config.citation_url,
                target: "_blank",
            },
            {
                title: _l("Interactive Tours"),
                url: "tours",
                target: "__use_router__",
            },
            {
                title: _l("Introduction to Galaxy"),
                url: "welcome/new",
            },
            {
                title: _l("About"),
                url: "about",
                target: "__use_router__",
            },
            {
                title: _l("Terms and Conditions"),
                url: config.terms_url,
                target: "_blank",
                hidden: !config.terms_url,
            },
        ],
    };
    menu.push(helpTab);

    //
    // User tab.
    //
    let userTab = {};
    if (!Galaxy.user.id) {
        if (config.allow_user_creation) {
            userTab = {
                id: MASTHEAD_TAB_ID.USER,
                title: _l("Login or Register"),
                cls: "loggedout-only",
                url: "login",
                tooltip: _l("Log in or register a new account"),
            };
        } else {
            userTab = {
                id: MASTHEAD_TAB_ID.USER,
                title: _l("Login"),
                cls: "loggedout-only",
                tooltip: _l("Login"),
                url: "login",
            };
        }
    } else {
        userTab = {
            id: MASTHEAD_TAB_ID.USER,
            title: _l("User"),
            cls: "loggedin-only",
            url: "javascript:void(0)",
            tooltip: _l("Account and saved data"),
            menu: [
                {
                    title: `${_l("Logged in as")} ${
                        Galaxy.user.get("username") ? Galaxy.user.get("username") : Galaxy.user.get("email")
                    }`,
                    disabled: true,
                },
                {
                    title: _l("Preferences"),
                    url: "user",
                    target: "__use_router__",
                },
                {
                    title: _l("Custom Builds"),
                    url: "custom_builds",
                    target: "__use_router__",
                },
                { divider: true },
                {
                    title: _l("Logout"),
                    onclick: userLogout,
                    hidden: config.single_user,
                },
                {
                    title: _l("Datasets"),
                    url: "datasets/list",
                    target: "__use_router__",
                },
                {
                    title: _l("Histories"),
                    url: "histories/list",
                    target: "__use_router__",
                },
                {
                    title: _l("Histories shared with me"),
                    url: "histories/list_shared",
                    target: "__use_router__",
                    hidden: config.single_user,
                },
                {
                    title: _l("Pages"),
                    url: "pages/list",
                    target: "__use_router__",
                },
                {
                    title: _l("Workflow Invocations"),
                    url: "workflows/invocations",
                    target: "__use_router__",
                },
            ],
        };
        if (mastheadOptions.enableVisualizations) {
            userTab.menu.push({
                title: _l("Visualizations"),
                url: "visualizations/list",
                target: "__use_router__",
            });
        }
        if (mastheadOptions.enableInteractiveTools) {
            userTab.menu.push({ divider: true });
            userTab.menu.push({
                title: _l("Active InteractiveTools"),
                url: "interactivetool_entry_points/list",
                target: "__use_router__",
            });
        }
    }
    menu.push(userTab);
    return menu;
}
