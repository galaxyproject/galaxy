import { getGalaxyInstance } from "app";
import { localize } from "utils/localization";
import { userLogout } from "utils/logout";
import { useUserStore } from "@/stores/userStore";

export function fetchMenu(options = {}) {
    const Galaxy = getGalaxyInstance();
    const userStore = useUserStore();
    const menu = [];
    //
    // Analyze data tab.
    //
    menu.push({
        id: "analysis",
        url: "/",
        tooltip: localize("Tools and Current History"),
        icon: "fa-home",
        target: "_top",
    });

    //
    // Workflow tab.
    //
    menu.push({
        id: "workflow",
        title: localize("Workflow"),
        tooltip: localize("Chain tools into workflows"),
        disabled: !Galaxy.user.id,
        url: "/workflows/list",
    });

    //
    // Visualization tab.
    //
    if (Galaxy.config.visualizations_visible) {
        menu.push({
            id: "visualization",
            title: localize("Visualize"),
            tooltip: localize("Visualize datasets"),
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
            title: localize("Data Libraries"),
            url: "/libraries",
            id: "libraries",
        });
    } else {
        menu.push({
            id: "shared",
            title: localize("Shared Data"),
            url: "javascript:void(0)",
            tooltip: localize("Access published resources"),
            menu: [
                {
                    title: localize("Data Libraries"),
                    url: "/libraries",
                    target: "_top",
                },
                {
                    title: localize("Histories"),
                    url: "/histories/list_published",
                },
                {
                    title: localize("Workflows"),
                    url: "/workflows/list_published",
                },
                {
                    title: localize("Visualizations"),
                    url: "/visualizations/list_published",
                },
                {
                    title: localize("Pages"),
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
            title: localize("Admin"),
            url: "/admin",
            tooltip: localize("Administer this Galaxy"),
            cls: "admin-only",
            target: "_top",
        });
    }

    //
    // Help tab.
    //
    const helpTab = {
        id: "help",
        title: localize("Help"),
        url: "javascript:void(0)",
        tooltip: localize("Support, contact, and community"),
        menu: [
            {
                title: localize("Galaxy Help"),
                url: options.helpsite_url,
                target: "_blank",
                hidden: !options.helpsite_url,
            },
            {
                title: localize("Support"),
                url: options.support_url,
                target: "_blank",
                hidden: !options.support_url,
            },
            {
                title: localize("Videos"),
                url: options.screencasts_url,
                target: "_blank",
                hidden: !options.screencasts_url,
            },
            {
                title: localize("Community Hub"),
                url: options.wiki_url,
                target: "_blank",
                hidden: !options.wiki_url,
            },
            {
                title: localize("How to Cite Galaxy"),
                url: options.citation_url,
                target: "_blank",
            },
            {
                title: localize("Interactive Tours"),
                url: "/tours",
            },
            {
                title: localize("Introduction to Galaxy"),
                url: "/welcome/new",
            },
            {
                title: localize("About"),
                url: "/about",
            },
            {
                title: localize("Terms and Conditions"),
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
                title: localize("Login or Register"),
                cls: "loggedout-only",
                url: "/login",
                tooltip: localize("Log in or register a new account"),
                target: "_top",
            };
        } else {
            userTab = {
                id: "user",
                title: localize("Login"),
                cls: "loggedout-only",
                tooltip: localize("Login"),
                url: "/login",
                target: "_top",
            };
        }
    } else {
        userTab = {
            id: "user",
            title: localize("User"),
            cls: "loggedin-only",
            url: "javascript:void(0)",
            tooltip: localize("Account and saved data"),
            menu: [
                {
                    title: `${localize("Signed in as")} ${
                        Galaxy.user.get("username") ? Galaxy.user.get("username") : Galaxy.user.get("email")
                    }`,
                    disabled: true,
                },
                { divider: true },
                {
                    title: localize("Preferences"),
                    url: "/user",
                },
                {
                    title: localize("Show/Hide Activity Bar"),
                    onclick: () => {
                        userStore.toggleActivityBar();
                    },
                },
                { divider: true },
                {
                    title: localize("Datasets"),
                    url: "/datasets/list",
                },
                {
                    title: localize("Histories"),
                    url: "/histories/list",
                },
                {
                    title: localize("Histories shared with me"),
                    url: "/histories/list_shared",
                    hidden: Galaxy.config.single_user,
                },
                {
                    title: localize("Pages"),
                    url: "/pages/list",
                },
                {
                    title: localize("Workflow Invocations"),
                    url: "/workflows/invocations",
                },
            ],
        };
        if (Galaxy.config.visualizations_visible) {
            userTab.menu.push({
                title: localize("Visualizations"),
                url: "/visualizations/list",
            });
        }
        if (Galaxy.config.interactivetools_enable) {
            userTab.menu.push({
                title: localize("Active InteractiveTools"),
                url: "/interactivetool_entry_points/list",
            });
        }
        userTab.menu.push({ divider: true });
        userTab.menu.push({
            title: localize("Sign Out"),
            onclick: userLogout,
            hidden: Galaxy.config.single_user,
        });
    }
    menu.push(userTab);
    return menu;
}
