/** Masthead Collection **/
import GenericNav from "layout/generic-nav-view";
import Webhooks from "mvc/webhooks";
import _l from "utils/localization";
import Utils from "utils/utils";
var Collection = Backbone.Collection.extend({
    model: Backbone.Model.extend({
        defaults: {
            visible: true,
            target: "_parent"
        }
    }),
    fetch: function(options) {
        var self = this;
        options = options || {};
        this.reset();

        //
        // Chat server tab
        //
        var extendedNavItem = new GenericNav.GenericNavView();
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
            url: "workflows/list"
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
                    url: "histories/list_published"
                },
                {
                    title: _l("Workflows"),
                    url: "workflows/list_published"
                },
                {
                    title: _l("Visualizations"),
                    url: "visualizations/list_published"
                },
                {
                    title: _l("Pages"),
                    url: "pages/list_published"
                }
            ]
        });

        //
        // Visualization tab.
        //
        this.add({
            id: "visualization",
            title: _l("Visualization"),
            url: "visualizations/list",
            tooltip: _l("Visualize datasets"),
            disabled: !Galaxy.user.id,
            menu: [
                {
                    title: _l("New Track Browser"),
                    url: "visualization/trackster",
                    target: "_frame"
                },
                {
                    title: _l("Saved Visualizations"),
                    url: "visualizations/list",
                    target: "_frame"
                },
                {
                    title: _l("Interactive Environments"),
                    url: "visualization/gie_list",
                    target: "galaxy_main"
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
                                onclick: webhook.config.function && new Function(webhook.config.function)
                            };

                            // Galaxy.page is undefined for data libraries, workflows pages
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
        Galaxy.user.get("is_admin") &&
            this.add({
                id: "admin",
                title: _l("Admin"),
                url: "admin",
                tooltip: _l("Administer this Galaxy"),
                cls: "admin-only"
            });

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
        options.terms_url &&
            helpTab.menu.push({
                title: _l("Terms and Conditions"),
                url: options.terms_url,
                target: "_blank"
            });
        options.biostar_url &&
            helpTab.menu.unshift({
                title: _l("Ask a question"),
                url: "biostar/biostar_question_redirect",
                target: "_blank"
            });
        options.biostar_url &&
            helpTab.menu.unshift({
                title: _l("Galaxy Biostar"),
                url: options.biostar_url_redirect,
                target: "_blank"
            });
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
                    tooltip: _l("Account registration or login"),
                    menu: [
                        {
                            title: _l("Login"),
                            url: "user/login",
                            target: "galaxy_main",
                            noscratchbook: true
                        },
                        {
                            title: _l("Register"),
                            url: "user/create",
                            target: "galaxy_main",
                            noscratchbook: true
                        }
                    ]
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
                        url: "user"
                    },
                    {
                        title: _l("Custom Builds"),
                        url: "custom_builds"
                    },
                    {
                        title: _l("Logout"),
                        url: `user/logout?session_csrf_token=${Galaxy.session_csrf_token}`,
                        target: "_top",
                        divider: true
                    },
                    {
                        title: _l("Saved Histories"),
                        url: "histories/list",
                        target: "_top"
                    },
                    {
                        title: _l("Saved Datasets"),
                        url: "datasets/list",
                        target: "_top"
                    },
                    {
                        title: _l("Saved Pages"),
                        url: "pages/list",
                        target: "_top"
                    }
                ]
            };
        }
        this.add(userTab);
        var activeView = this.get(options.active_view);
        activeView && activeView.set("active", true);
        return new jQuery.Deferred().resolve().promise();
    }
});

/** Masthead tab **/
var Tab = Backbone.View.extend({
    initialize: function(options) {
        this.model = options.model;
        this.setElement(this._template());
        this.$dropdown = this.$(".dropdown");
        this.$toggle = this.$(".dropdown-toggle");
        this.$menu = this.$(".dropdown-menu");
        this.$note = this.$(".dropdown-note");
        this.listenTo(this.model, "change", this.render, this);
    },

    events: {
        "click .dropdown-toggle": "_toggleClick"
    },

    render: function() {
        var self = this;
        $(".tooltip").remove();
        this.$el.attr("id", this.model.id).css({
            visibility: (this.model.get("visible") && "visible") || "hidden"
        });
        this.model.set("url", this._formatUrl(this.model.get("url")));
        this.$note
            .html(this.model.get("note") || "")
            .removeClass()
            .addClass("dropdown-note")
            .addClass(this.model.get("note_cls"))
            .css({
                display: (this.model.get("show_note") && "block") || "none"
            });
        this.$toggle
            .html(this.model.get("title") || "")
            .removeClass()
            .addClass("dropdown-toggle")
            .addClass(this.model.get("cls"))
            .addClass(this.model.get("icon") && `dropdown-icon fa ${this.model.get("icon")}`)
            .addClass(this.model.get("toggle") && "toggle")
            .attr("target", this.model.get("target"))
            .attr("href", this.model.get("url"))
            .attr("title", this.model.get("tooltip"))
            .tooltip("destroy");
        this.model.get("tooltip") && this.$toggle.tooltip({ placement: "bottom" });
        this.$dropdown
            .removeClass()
            .addClass("dropdown")
            .addClass(this.model.get("disabled") && "disabled")
            .addClass(this.model.get("active") && "active");
        if (this.model.get("menu") && this.model.get("show_menu")) {
            this.$menu.show();
            $("#dd-helper")
                .show()
                .off()
                .on("click", () => {
                    $("#dd-helper").hide();
                    self.model.set("show_menu", false);
                });
        } else {
            self.$menu.hide();
            $("#dd-helper").hide();
        }
        this.$menu.empty().removeClass("dropdown-menu");
        if (this.model.get("menu")) {
            _.each(this.model.get("menu"), menuItem => {
                self.$menu.append(self._buildMenuItem(menuItem));
                menuItem.divider && self.$menu.append($("<li/>").addClass("divider"));
            });
            self.$menu.addClass("dropdown-menu");
            self.$toggle.append($("<b/>").addClass("caret"));
        }
        return this;
    },

    /** Add new menu item */
    _buildMenuItem: function(options) {
        var self = this;
        options = _.defaults(options || {}, {
            title: "",
            url: "",
            target: "_parent",
            noscratchbook: false
        });
        options.url = self._formatUrl(options.url);
        return $("<li/>").append(
            $("<a/>")
                .attr("href", options.url)
                .attr("target", options.target)
                .html(options.title)
                .on("click", e => {
                    e.preventDefault();
                    self.model.set("show_menu", false);
                    if (options.onclick) {
                        options.onclick();
                    } else {
                        Galaxy.frame.add(options);
                    }
                })
        );
    },

    /** Handle click event */
    _toggleClick: function(e) {
        var self = this;
        var model = this.model;
        e.preventDefault();
        $(".tooltip").hide();
        model.trigger("dispatch", m => {
            model.id !== m.id && m.get("menu") && m.set("show_menu", false);
        });
        if (!model.get("disabled")) {
            if (!model.get("menu")) {
                model.get("onclick") ? model.get("onclick")() : Galaxy.frame.add(model.attributes);
            } else {
                model.set("show_menu", true);
            }
        } else {
            function buildLink(label, url) {
                return $("<div/>")
                    .append(
                        $("<a/>")
                            .attr("href", Galaxy.root + url)
                            .html(label)
                    )
                    .html();
            }
            this.$toggle.popover && this.$toggle.popover("destroy");
            this.$toggle
                .popover({
                    html: true,
                    placement: "bottom",
                    content: `Please ${buildLink("login", "user/login?use_panels=True")} or ${buildLink(
                        "register",
                        "user/create?use_panels=True"
                    )} to use this feature.`
                })
                .popover("show");
            setTimeout(() => {
                self.$toggle.popover("destroy");
            }, 5000);
        }
    },

    /** Url formatting */
    _formatUrl: function(url) {
        return typeof url == "string" && url.indexOf("//") === -1 && url.charAt(0) != "/" ? Galaxy.root + url : url;
    },

    /** body tempate */
    _template: function() {
        return (
            '<ul class="nav navbar-nav">' +
            '<li class="dropdown">' +
            '<a class="dropdown-toggle"/>' +
            '<ul class="dropdown-menu"/>' +
            '<div class="dropdown-note"/>' +
            "</li>" +
            "</ul>"
        );
    }
});

export default {
    Collection: Collection,
    Tab: Tab
};
