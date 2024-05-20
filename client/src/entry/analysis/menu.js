import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import { userLogout } from "utils/logout";

import { useUserStore } from "@/stores/userStore";

export function fetchMenu(options = {}) {
    const Galaxy = getGalaxyInstance();
    const menu = [];
    //
    // Help tab.
    //
    const helpTab = {
        id: "help",
        icon: "fa fa-question",
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
                title: _l("Log in or Register"),
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
            icon: "fa fa-sign-out-alt",
            cls: "loggedin-only",
            onclick: userLogout,
            hidden: Galaxy.config.single_user,
            tooltip: _l("Logout"),
        };
    }
    menu.push(userTab);
    return menu;
}
