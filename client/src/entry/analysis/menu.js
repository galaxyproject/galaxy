import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import { userLogout } from "utils/logout";

export function fetchMenu(options = {}) {
    const Galaxy = getGalaxyInstance();
    const menu = [];
    //
    // Analyze data tab.
    //
    menu.push({
        id: "analysis",
        url: "/",
        tooltip: _l("Tools and Current History"),
        icon: "fa-home",
        target: "_top",
    });

    //
    // Workflow tab.
    //
    menu.push({
        id: "workflow",
        title: _l("Workflow"),
        tooltip: _l("Chain tools into workflows"),
        disabled: !Galaxy.user.id,
        url: "/workflows/list",
    });

    //
    // Visualization tab.
    //
    if (Galaxy.config.visualizations_visible) {
        menu.push({
            id: "visualization",
            title: _l("Visualize"),
            tooltip: _l("Visualize datasets"),
            disabled: !Galaxy.user.id,
            url: "/visualizations",
        });
    }

    //
    // 'Shared Items' or Libraries tab.
    //
    if (Galaxy.config.single_user) {
        // Single user can still use libraries, especially as we may grow that
        // functionality as a representation for external data.  The rest is
        // hidden though.
        menu.push({
            title: _l("Data Libraries"),
            url: "/libraries",
            id: "libraries",
        });
    } else {
        menu.push({
            id: "shared",
            title: _l("Shared Data"),
            url: "javascript:void(0)",
            tooltip: _l("Access published resources"),
            menu: [
                {
                    title: _l("Data Libraries"),
                    url: "/libraries",
                    target: "_top",
                },
                {
                    title: _l("Histories"),
                    url: "/histories/list_published",
                },
                {
                    title: _l("Workflows"),
                    url: "/workflows/list_published",
                },
                {
                    title: _l("Visualizations"),
                    url: "/visualizations/list_published",
                },
                {
                    title: _l("Pages"),
                    url: "/pages/list_published",
                },
            ],
        });
    }

    //
    // Admin.
    //
    if (Galaxy.user.get("is_admin")) {
        menu.push({
            id: "admin",
            title: _l("Admin"),
            url: "/admin",
            tooltip: _l("Administer this Galaxy"),
            cls: "admin-only",
            target: "_top",
        });
    }

    //
    // Help tab.
    //
    const helpTab = {
        id: "help",
        title: _l("Help"),
        url: "javascript:void(0)",
        tooltip: _l("Support, contact, and community"),
        menu: [
            {
                title: _l("Galaxy Help"),
                url: options.helpsite_url,
                target: "_blank",
                hidden: !options.helpsite_url,
            },
            {
                title: _l("Support"),
                url: options.support_url,
                target: "_blank",
                hidden: !options.support_url,
            },
            {
                title: _l("Videos"),
                url: options.screencasts_url,
                target: "_blank",
                hidden: !options.screencasts_url,
            },
            {
                title: _l("Community Hub"),
                url: options.wiki_url,
                target: "_blank",
                hidden: !options.wiki_url,
            },
            {
                title: _l("How to Cite Galaxy"),
                url: options.citation_url,
                target: "_blank",
            },
            {
                title: _l("Interactive Tours"),
                url: "/tours",
            },
            {
                title: _l("Introduction to Galaxy"),
                url: "/welcome/new",
            },
            {
                title: _l("About"),
                url: "/about",
            },
            {
                title: _l("Terms and Conditions"),
                url: options.terms_url,
                target: "_blank",
                hidden: !options.terms_url,
            },
        ],
    };
    menu.push(helpTab);

    //
    // User tab.
    //
    let userTab = {};
    if (!Galaxy.user.id) {
        if (options.allow_user_creation) {
            userTab = {
                id: "user",
                title: _l("Login or Register"),
                cls: "loggedout-only",
                url: "/login",
                tooltip: _l("Log in or register a new account"),
                target: "_top",
            };
        } else {
            userTab = {
                id: "user",
                title: _l("Login"),
                cls: "loggedout-only",
                tooltip: _l("Login"),
                url: "/login",
                target: "_top",
            };
        }
    } else {
        userTab = {
            id: "user",
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
                    url: "/user",
                },
                {
                    title: _l("Custom Builds"),
                    url: "/custom_builds",
                },
                { divider: true },
                {
                    title: _l("Logout"),
                    onclick: userLogout,
                    hidden: Galaxy.config.single_user,
                },
                {
                    title: _l("Datasets"),
                    url: "/datasets/list",
                },
                {
                    title: _l("Histories"),
                    url: "/histories/list",
                },
                {
                    title: _l("Histories shared with me"),
                    url: "/histories/list_shared",
                    hidden: Galaxy.config.single_user,
                },
                {
                    title: _l("Pages"),
                    url: "/pages/list",
                },
                {
                    title: _l("Workflow Invocations"),
                    url: "/workflows/invocations",
                },
            ],
        };
        if (Galaxy.config.visualizations_visible) {
            userTab.menu.push({
                title: _l("Visualizations"),
                url: "/visualizations/list",
            });
        }
        if (Galaxy.config.interactivetools_enable) {
            userTab.menu.push({ divider: true });
            userTab.menu.push({
                title: _l("Active InteractiveTools"),
                url: "/interactivetool_entry_points/list",
            });
        }
    }
    menu.push(userTab);
    return menu;
}
