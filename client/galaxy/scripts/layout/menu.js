/** Masthead Collection **/
import $ from "jquery";
import axios from "axios";
import Backbone from "backbone";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import { CommunicationServerView } from "layout/communication-server-view";
import Webhooks from "mvc/webhooks";
import Utils from "utils/utils";

export function logoutClick() {
    const galaxy = getGalaxyInstance();
    const session_csrf_token = galaxy.session_csrf_token;
    const url = `${galaxy.root}user/logout?session_csrf_token=${session_csrf_token}`;
    axios
        .get(url)
        .then(() => {
            if (galaxy.user) {
                galaxy.user.clearSessionStorage();
            }
            // Check if we need to logout of OIDC IDP
            if (galaxy.config.enable_oidc) {
                return axios.get(`${galaxy.root}authnz/logout`);
            } else {
                return {};
            }
        })
        .then((response) => {
            if (response.data && response.data.redirect_uri) {
                window.top.location.href = response.data.redirect_uri;
            } else {
                window.top.location.href = `${galaxy.root}root/login?is_logout_redirect=true`;
            }
        });
}

const Collection = Backbone.Collection.extend({
    model: Backbone.Model.extend({
        defaults: {
            visible: true,
            target: "_parent",
        },
    }),
    fetch: function (options) {
        options = options || {};
        this.reset();

        const Galaxy = getGalaxyInstance();

        //
        // Chat server tab
        //
        const extendedNavItem = new CommunicationServerView();
        this.add(extendedNavItem.render());

        //
        // Analyze data tab.
        //
        this.add({
            id: "analysis",
            title: _l("Analyze Data"),
            url: "",
            tooltip: _l("Analysis home view"),
        });

        //
        // Workflow tab.
        //
        this.add({
            id: "workflow",
            title: _l("Workflow"),
            tooltip: _l("Chain tools into workflows"),
            disabled: !Galaxy.user.id,
            url: "workflows/list",
            target: "__use_router__",
        });

        //
        // Visualization tab.
        //
        if (Galaxy.config.visualizations_visible) {
            this.add({
                id: "visualization",
                title: _l("Visualize"),
                url: "javascript:void(0)",
                tooltip: _l("Visualize datasets"),
                disabled: !Galaxy.user.id,
                menu: [
                    {
                        title: _l("Create Visualization"),
                        url: "visualizations",
                        target: "__use_router__",
                    },
                    {
                        title: _l("Interactive Environments"),
                        url: "visualization/gie_list",
                        target: "galaxy_main",
                    },
                ],
            });
        }

        //
        // 'Shared Items' or Libraries tab.
        //
        this.add({
            id: "shared",
            title: _l("Shared Data"),
            url: "javascript:void(0)",
            tooltip: _l("Access published resources"),
            menu: [
                {
                    title: _l("Data Libraries"),
                    url: "library/list",
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

        //
        // Webhooks
        //
        Webhooks.load({
            type: "masthead",
            callback: function (webhooks) {
                $(document).ready(() => {
                    webhooks.each((model) => {
                        const webhook = model.toJSON();
                        if (webhook.activate) {
                            const obj = {
                                id: webhook.id,
                                icon: webhook.config.icon,
                                url: webhook.config.url,
                                tooltip: webhook.config.tooltip,
                                /*jslint evil: true */
                                onclick: webhook.config.function && new Function(webhook.config.function),
                            };

                            // Galaxy.page is undefined for data libraries, workflows pages
                            const Galaxy = getGalaxyInstance();
                            if (Galaxy.page) {
                                Galaxy.page.masthead.collection.add(obj);
                            } else if (Galaxy.masthead) {
                                Galaxy.masthead.collection.add(obj);
                            }

                            // Append masthead script and styles to Galaxy main
                            Utils.appendScriptStyle(webhook);
                        }
                    });
                });
            },
        });

        //
        // Admin.
        //
        if (Galaxy.user.get("is_admin")) {
            this.add({
                id: "admin",
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
            id: "help",
            title: _l("Help"),
            url: "javascript:void(0)",
            tooltip: _l("Support, contact, and community"),
            menu: [
                {
                    title: _l("Support"),
                    url: options.support_url,
                    target: "_blank",
                },
                {
                    title: _l("Search"),
                    url: options.search_url,
                    target: "_blank",
                },
                {
                    title: _l("Mailing Lists"),
                    url: options.mailing_lists,
                    target: "_blank",
                },
                {
                    title: _l("Videos"),
                    url: options.screencasts_url,
                    target: "_blank",
                },
                {
                    title: _l("Wiki"),
                    url: options.wiki_url,
                    target: "_blank",
                },
                {
                    title: _l("How to Cite Galaxy"),
                    url: options.citation_url,
                    target: "_blank",
                },
                {
                    title: _l("Interactive Tours"),
                    url: "tours",
                },
            ],
        };
        if (options.terms_url) {
            helpTab.menu.push({
                title: _l("Terms and Conditions"),
                url: options.terms_url,
                target: "_blank",
            });
        }
        if (options.helpsite_url) {
            helpTab.menu.unshift({
                title: _l("Galaxy Help"),
                url: options.helpsite_url,
                target: "_blank",
            });
        }
        this.add(helpTab);

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
                    url: "login",
                    tooltip: _l("Log in or register a new account"),
                };
            } else {
                userTab = {
                    id: "user",
                    title: _l("Login"),
                    cls: "loggedout-only",
                    tooltip: _l("Login"),
                    url: "login",
                    noscratchbook: true,
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
                        title: `${_l("Logged in as")} ${Galaxy.user.get("email")}`,
                        class: "dropdown-item disabled",
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
                    {
                        title: _l("Logout"),
                        divider: true,
                        onclick: logoutClick,
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
            if (Galaxy.config.visualizations_visible) {
                userTab.menu.push({
                    title: _l("Visualizations"),
                    url: "visualizations/list",
                    target: "__use_router__",
                });
            }
            if (Galaxy.config.interactivetools_enable) {
                userTab.menu[userTab.menu.length - 1].divider = true;
                userTab.menu.push({
                    title: _l("Active InteractiveTools"),
                    url: "interactivetool_entry_points/list",
                    target: "__use_router__",
                });
            }
        }
        this.add(userTab);
        return new $.Deferred().resolve().promise();
    },
});

export default {
    Collection: Collection,
};
