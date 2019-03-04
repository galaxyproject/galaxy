/** Masthead Collection **/
import _ from "underscore";
import $ from "jquery";
import axios from "axios";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import { CommunicationServerView } from "layout/communication-server-view";
import Webhooks from "mvc/webhooks";
import Utils from "utils/utils";

function logoutClick() {
    let galaxy = getGalaxyInstance();
    let session_csrf_token = galaxy.session_csrf_token;
    let url = `${galaxy.root}user/logout?session_csrf_token=${session_csrf_token}`;
    axios.get(url).then(() => {
        if (galaxy.user) {
            galaxy.user.clearSessionStorage();
        }
        window.top.location.href = `${galaxy.root}login`;
    });
}

var Collection = Backbone.Collection.extend({
    model: Backbone.Model.extend({
        defaults: {
            visible: true,
            target: "_parent"
        }
    }),
    fetch: function(options) {
        options = options || {};
        this.reset();

        let Galaxy = getGalaxyInstance();

        //
        // Chat server tab
        //
        var extendedNavItem = new CommunicationServerView();
        this.add(extendedNavItem.render());

        //
        // Analyze data tab.
        //
        this.add({
            id: "analysis",
            title: _l("Analyze Data"),
            url: "",
            tooltip: _l("Analysis home view")
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
            target: "__use_router__"
        });

        //
        // Visualization tab.
        //
        this.add({
            id: "visualization",
            title: _l("Visualize"),
            tooltip: _l("Visualize datasets"),
            disabled: !Galaxy.user.id,
            menu: [
                {
                    title: _l("Create Visualization"),
                    url: "visualizations",
                    target: "__use_router__"
                },
                {
                    title: _l("Interactive Environments"),
                    url: "visualization/gie_list",
                    target: "galaxy_main"
                }
            ]
        });

        //
        // 'Shared Items' or Libraries tab.
        //
        this.add({
            id: "shared",
            title: _l("Shared Data"),
            url: "library/index",
            tooltip: _l("Access published resources"),
            menu: [
                {
                    title: _l("Data Libraries"),
                    url: "library/list"
                },
                {
                    title: _l("Histories"),
                    url: "histories/list_published",
                    target: "__use_router__"
                },
                {
                    title: _l("Workflows"),
                    url: "workflows/list_published",
                    target: "__use_router__"
                },
                {
                    title: _l("Visualizations"),
                    url: "visualizations/list_published",
                    target: "__use_router__"
                },
                {
                    title: _l("Pages"),
                    url: "pages/list_published",
                    target: "__use_router__"
                }
            ]
        });

        //
        // Webhooks
        //
        Webhooks.load({
            type: "masthead",
            callback: function(webhooks) {
                $(document).ready(() => {
                    webhooks.each(model => {
                        var webhook = model.toJSON();
                        if (webhook.activate) {
                            var obj = {
                                id: webhook.id,
                                icon: webhook.config.icon,
                                url: webhook.config.url,
                                tooltip: webhook.config.tooltip,
                                /*jslint evil: true */
                                onclick: webhook.config.function && new Function(webhook.config.function)
                            };

                            // Galaxy.page is undefined for data libraries, workflows pages
                            let Galaxy = getGalaxyInstance();
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
            }
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
                cls: "admin-only"
            });
        }

        //
        // Help tab.
        //
        var helpTab = {
            id: "help",
            title: _l("Help"),
            tooltip: _l("Support, contact, and community"),
            menu: [
                {
                    title: _l("Support"),
                    url: options.support_url,
                    target: "_blank"
                },
                {
                    title: _l("Search"),
                    url: options.search_url,
                    target: "_blank"
                },
                {
                    title: _l("Mailing Lists"),
                    url: options.mailing_lists,
                    target: "_blank"
                },
                {
                    title: _l("Videos"),
                    url: options.screencasts_url,
                    target: "_blank"
                },
                {
                    title: _l("Wiki"),
                    url: options.wiki_url,
                    target: "_blank"
                },
                {
                    title: _l("How to Cite Galaxy"),
                    url: options.citation_url,
                    target: "_blank"
                },
                {
                    title: _l("Interactive Tours"),
                    url: "tours"
                }
            ]
        };
        if (options.terms_url) {
            helpTab.menu.push({
                title: _l("Terms and Conditions"),
                url: options.terms_url,
                target: "_blank"
            });
        }
        if (options.biostar_url) {
            helpTab.menu.unshift({
                title: _l("Ask a question"),
                url: "biostar/biostar_question_redirect",
                target: "_blank"
            });
        }
        if (options.biostar_url) {
            helpTab.menu.unshift({
                title: _l("Galaxy Biostar"),
                url: options.biostar_url_redirect,
                target: "_blank"
            });
        }
        if (options.helpsite_url) {
            helpTab.menu.unshift({
                title: _l("Galaxy Help"),
                url: options.helpsite_url,
                target: "_blank"
            });
        }
        this.add(helpTab);

        //
        // User tab.
        //
        var userTab = {};
        if (!Galaxy.user.id) {
            if (options.allow_user_creation) {
                userTab = {
                    id: "user",
                    title: _l("Login or Register"),
                    cls: "loggedout-only",
                    url: "login",
                    tooltip: _l("Account registration or login")
                };
            } else {
                userTab = {
                    id: "user",
                    title: _l("Login"),
                    cls: "loggedout-only",
                    tooltip: _l("Login"),
                    url: "user/login",
                    target: "galaxy_main",
                    noscratchbook: true
                };
            }
        } else {
            userTab = {
                id: "user",
                title: _l("User"),
                cls: "loggedin-only",
                tooltip: _l("Account and saved data"),
                menu: [
                    {
                        title: `${_l("Logged in as")} ${Galaxy.user.get("email")}`
                    },
                    {
                        title: _l("Preferences"),
                        url: "user",
                        target: "__use_router__"
                    },
                    {
                        title: _l("Custom Builds"),
                        url: "custom_builds",
                        target: "__use_router__"
                    },
                    {
                        title: _l("Logout"),
                        divider: true,
                        onclick: logoutClick
                    },
                    {
                        title: _l("Saved Datasets"),
                        url: "datasets/list",
                        target: "__use_router__"
                    },
                    {
                        title: _l("Saved Histories"),
                        url: "histories/list",
                        target: "__use_router__"
                    },
                    {
                        title: _l("Saved Pages"),
                        url: "pages/list",
                        target: "__use_router__"
                    },
                    {
                        title: _l("Saved Visualizations"),
                        url: "visualizations/list",
                        target: "__use_router__"
                    }
                ]
            };
        }
        this.add(userTab);
        return new $.Deferred().resolve().promise();
    }
});

/** Masthead tab **/
var Tab = Backbone.View.extend({
    initialize: function(options) {
        this.model = options.model;
        this.setElement(this._template());
        this.$link = this.$(".nav-link");
        this.$note = this.$(".nav-note");
        this.$menu = this.$(".dropdown-menu");
        this.listenTo(this.model, "change", this.render, this);
    },

    events: {
        "click .nav-link": "_toggleClick"
    },

    render: function() {
        $(".tooltip").remove();
        this.$el
            .removeClass()
            .addClass(this.model.get("disabled") && "disabled")
            .addClass(this.model.get("active") && "active")
            .addClass(this.model.get("menu") && "dropdown")
            .attr("id", this.model.id)
            .css({
                visibility: (this.model.get("visible") && "visible") || "hidden"
            });
        this.model.set("url", this._formatUrl(this.model.get("url")));
        this.$note
            .html(this.model.get("note") || "")
            .removeClass()
            .addClass("nav-note")
            .addClass(this.model.get("note_cls"))
            .css({
                display: (this.model.get("show_note") && "block") || "none"
            });
        this.$link
            .html(this.model.get("title") || "")
            .removeClass()
            .addClass("nav-link")
            .addClass(this.model.get("cls"))
            .addClass(this.model.get("icon") && `nav-icon fa ${this.model.get("icon")}`)
            .addClass(this.model.get("menu") && "dropdown-toggle")
            .addClass(this.model.get("toggle") && "toggle")
            .attr("target", this.model.get("target"))
            .attr("href", this.model.get("url"))
            .attr("title", this.model.get("tooltip"))
            .tooltip("dispose");
        if (this.model.get("tooltip")) {
            this.$link.tooltip({ placement: "bottom" });
        }
        if (this.model.get("menu") && this.model.get("show_menu")) {
            this.$menu.show();
            $("#dd-helper")
                .show()
                .off()
                .on("click", () => {
                    $("#dd-helper").hide();
                    this.model.set("show_menu", false);
                });
        } else {
            this.$menu.hide();
            $("#dd-helper").hide();
        }
        this.$menu.empty().removeClass();
        if (this.model.get("menu")) {
            _.each(this.model.get("menu"), menuItem => {
                this.$menu.append(this._buildMenuItem(menuItem));
                if (menuItem.divider) {
                    this.$menu.append($("<div/>").addClass("dropdown-divider"));
                }
            });
            this.$menu.addClass("dropdown-menu");
            this.$link.append($("<b/>").addClass("caret"));
        }
        return this;
    },

    /** Add new menu item */
    _buildMenuItem: function(options) {
        options = _.defaults(options || {}, {
            title: "",
            url: "",
            target: "_parent",
            noscratchbook: false
        });
        options.url = this._formatUrl(options.url);
        return $("<a/>")
            .addClass("dropdown-item")
            .attr("href", options.url)
            .attr("target", options.target)
            .html(options.title)
            .on("click", e => {
                e.preventDefault();
                this.model.set("show_menu", false);
                if (options.onclick) {
                    options.onclick();
                } else {
                    let Galaxy = getGalaxyInstance();
                    if (options.target == "__use_router__" && typeof Galaxy.page != "undefined") {
                        Galaxy.page.router.push(options.url);
                    } else {
                        try {
                            Galaxy.frame.add(options);
                        } catch (err) {
                            console.warn("Missing frame element on galaxy instance", err);
                        }
                    }
                }
            });
    },

    buildLink: function(label, url) {
        return $("<div/>")
            .append(
                $("<a/>")
                    .attr("href", getAppRoot() + url)
                    .html(label)
            )
            .html();
    },

    /** Handle click event */
    _toggleClick: function(e) {
        var model = this.model;
        e.preventDefault();
        $(".tooltip").hide();
        model.trigger("dispatch", m => {
            if (model.id !== m.id && m.get("menu")) {
                m.set("show_menu", false);
            }
        });
        if (!model.get("disabled")) {
            if (!model.get("menu")) {
                if (model.get("onclick")) {
                    model.get("onclick")();
                } else {
                    let Galaxy = getGalaxyInstance();
                    if (model.attributes.target == "__use_router__" && typeof Galaxy.page != "undefined") {
                        Galaxy.page.router.push(model.attributes.url);
                    } else {
                        Galaxy.frame.add(model.attributes);
                    }
                }
            } else {
                model.set("show_menu", true);
            }
        } else {
            if (this.$link.popover) {
                this.$link.popover("dispose");
            }
            this.$link
                .popover({
                    html: true,
                    placement: "bottom",
                    content: `Please ${this.buildLink("login or register", "login")} to use this feature.`
                })
                .popover("show");
            window.setTimeout(() => {
                this.$link.popover("dispose");
            }, 3000);
        }
    },

    /** Url formatting */
    _formatUrl: function(url) {
        return typeof url == "string" && url.indexOf("//") === -1 && url.charAt(0) != "/" ? getAppRoot() + url : url;
    },

    /** body tempate */
    _template: function() {
        return `
            <li class="nav-item">
                <a class="nav-link"/>
                <div class="nav-note"/>
                <div class="dropdown-menu"/>
            </li>`;
    }
});

export default {
    Collection: Collection,
    Tab: Tab
};
