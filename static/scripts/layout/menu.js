define("layout/menu", ["exports", "layout/generic-nav-view", "mvc/webhooks", "utils/localization", "utils/utils"], function(exports, _genericNavView, _webhooks, _localization, _utils) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _genericNavView2 = _interopRequireDefault(_genericNavView);

    var _webhooks2 = _interopRequireDefault(_webhooks);

    var _localization2 = _interopRequireDefault(_localization);

    var _utils2 = _interopRequireDefault(_utils);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    /** Masthead Collection **/
    var Collection = Backbone.Collection.extend({
        model: Backbone.Model.extend({
            defaults: {
                visible: true,
                target: "_parent"
            }
        }),
        fetch: function fetch(options) {
            var self = this;
            options = options || {};
            this.reset();

            //
            // Chat server tab
            //
            var extendedNavItem = new _genericNavView2.default.GenericNavView();
            this.add(extendedNavItem.render());

            //
            // Analyze data tab.
            //
            this.add({
                id: "analysis",
                title: (0, _localization2.default)("Analyze Data"),
                url: "",
                tooltip: (0, _localization2.default)("Analysis home view")
            });

            //
            // Workflow tab.
            //
            this.add({
                id: "workflow",
                title: (0, _localization2.default)("Workflow"),
                tooltip: (0, _localization2.default)("Chain tools into workflows"),
                disabled: !Galaxy.user.id,
                url: "workflows/list"
            });

            //
            // 'Shared Items' or Libraries tab.
            //
            this.add({
                id: "shared",
                title: (0, _localization2.default)("Shared Data"),
                url: "library/index",
                tooltip: (0, _localization2.default)("Access published resources"),
                menu: [{
                    title: (0, _localization2.default)("Data Libraries"),
                    url: "library/list"
                }, {
                    title: (0, _localization2.default)("Histories"),
                    url: "histories/list_published"
                }, {
                    title: (0, _localization2.default)("Workflows"),
                    url: "workflows/list_published"
                }, {
                    title: (0, _localization2.default)("Visualizations"),
                    url: "visualizations/list_published"
                }, {
                    title: (0, _localization2.default)("Pages"),
                    url: "pages/list_published"
                }]
            });

            //
            // Visualization tab.
            //
            this.add({
                id: "visualization",
                title: (0, _localization2.default)("Visualization"),
                url: "visualizations/list",
                tooltip: (0, _localization2.default)("Visualize datasets"),
                disabled: !Galaxy.user.id,
                menu: [{
                    title: (0, _localization2.default)("New Track Browser"),
                    url: "visualization/trackster",
                    target: "_frame"
                }, {
                    title: (0, _localization2.default)("Saved Visualizations"),
                    url: "visualizations/list",
                    target: "_frame"
                }, {
                    title: (0, _localization2.default)("Interactive Environments"),
                    url: "visualization/gie_list",
                    target: "galaxy_main"
                }]
            });

            //
            // Webhooks
            //
            _webhooks2.default.add({
                url: "api/webhooks/masthead/all",
                callback: function callback(webhooks) {
                    $(document).ready(function() {
                        $.each(webhooks.models, function(index, model) {
                            var webhook = model.toJSON();
                            if (webhook.activate) {
                                var obj = {
                                    id: webhook.name,
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
                                _utils2.default.appendScriptStyle(webhook);
                            }
                        });
                    });
                }
            });

            //
            // Admin.
            //
            Galaxy.user.get("is_admin") && this.add({
                id: "admin",
                title: (0, _localization2.default)("Admin"),
                url: "admin",
                tooltip: (0, _localization2.default)("Administer this Galaxy"),
                cls: "admin-only"
            });

            //
            // Help tab.
            //
            var helpTab = {
                id: "help",
                title: (0, _localization2.default)("Help"),
                tooltip: (0, _localization2.default)("Support, contact, and community"),
                menu: [{
                    title: (0, _localization2.default)("Support"),
                    url: options.support_url,
                    target: "_blank"
                }, {
                    title: (0, _localization2.default)("Search"),
                    url: options.search_url,
                    target: "_blank"
                }, {
                    title: (0, _localization2.default)("Mailing Lists"),
                    url: options.mailing_lists,
                    target: "_blank"
                }, {
                    title: (0, _localization2.default)("Videos"),
                    url: options.screencasts_url,
                    target: "_blank"
                }, {
                    title: (0, _localization2.default)("Wiki"),
                    url: options.wiki_url,
                    target: "_blank"
                }, {
                    title: (0, _localization2.default)("How to Cite Galaxy"),
                    url: options.citation_url,
                    target: "_blank"
                }, {
                    title: (0, _localization2.default)("Interactive Tours"),
                    url: "tours"
                }]
            };
            options.terms_url && helpTab.menu.push({
                title: (0, _localization2.default)("Terms and Conditions"),
                url: options.terms_url,
                target: "_blank"
            });
            options.biostar_url && helpTab.menu.unshift({
                title: (0, _localization2.default)("Ask a question"),
                url: "biostar/biostar_question_redirect",
                target: "_blank"
            });
            options.biostar_url && helpTab.menu.unshift({
                title: (0, _localization2.default)("Galaxy Biostar"),
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
                        title: (0, _localization2.default)("Login or Register"),
                        cls: "loggedout-only",
                        tooltip: (0, _localization2.default)("Account registration or login"),
                        menu: [{
                            title: (0, _localization2.default)("Login"),
                            url: "user/login",
                            target: "galaxy_main",
                            noscratchbook: true
                        }, {
                            title: (0, _localization2.default)("Register"),
                            url: "user/create",
                            target: "galaxy_main",
                            noscratchbook: true
                        }]
                    };
                } else {
                    userTab = {
                        id: "user",
                        title: (0, _localization2.default)("Login"),
                        cls: "loggedout-only",
                        tooltip: (0, _localization2.default)("Login"),
                        url: "user/login",
                        target: "galaxy_main",
                        noscratchbook: true
                    };
                }
            } else {
                userTab = {
                    id: "user",
                    title: (0, _localization2.default)("User"),
                    cls: "loggedin-only",
                    tooltip: (0, _localization2.default)("Account and saved data"),
                    menu: [{
                        title: (0, _localization2.default)("Logged in as") + " " + Galaxy.user.get("email")
                    }, {
                        title: (0, _localization2.default)("Preferences"),
                        url: "user"
                    }, {
                        title: (0, _localization2.default)("Custom Builds"),
                        url: "custom_builds"
                    }, {
                        title: (0, _localization2.default)("Logout"),
                        url: "user/logout?session_csrf_token=" + Galaxy.session_csrf_token,
                        target: "_top",
                        divider: true
                    }, {
                        title: (0, _localization2.default)("Saved Histories"),
                        url: "histories/list",
                        target: "_top"
                    }, {
                        title: (0, _localization2.default)("Saved Datasets"),
                        url: "datasets/list",
                        target: "_top"
                    }, {
                        title: (0, _localization2.default)("Saved Pages"),
                        url: "pages/list",
                        target: "_top"
                    }]
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
        initialize: function initialize(options) {
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

        render: function render() {
            var self = this;
            $(".tooltip").remove();
            this.$el.attr("id", this.model.id).css({
                visibility: this.model.get("visible") && "visible" || "hidden"
            });
            this.model.set("url", this._formatUrl(this.model.get("url")));
            this.$note.html(this.model.get("note") || "").removeClass().addClass("dropdown-note").addClass(this.model.get("note_cls")).css({
                display: this.model.get("show_note") && "block" || "none"
            });
            this.$toggle.html(this.model.get("title") || "").removeClass().addClass("dropdown-toggle").addClass(this.model.get("cls")).addClass(this.model.get("icon") && "dropdown-icon fa " + this.model.get("icon")).addClass(this.model.get("toggle") && "toggle").attr("target", this.model.get("target")).attr("href", this.model.get("url")).attr("title", this.model.get("tooltip")).tooltip("destroy");
            this.model.get("tooltip") && this.$toggle.tooltip({
                placement: "bottom"
            });
            this.$dropdown.removeClass().addClass("dropdown").addClass(this.model.get("disabled") && "disabled").addClass(this.model.get("active") && "active");
            if (this.model.get("menu") && this.model.get("show_menu")) {
                this.$menu.show();
                $("#dd-helper").show().off().on("click", function() {
                    $("#dd-helper").hide();
                    self.model.set("show_menu", false);
                });
            } else {
                self.$menu.hide();
                $("#dd-helper").hide();
            }
            this.$menu.empty().removeClass("dropdown-menu");
            if (this.model.get("menu")) {
                _.each(this.model.get("menu"), function(menuItem) {
                    self.$menu.append(self._buildMenuItem(menuItem));
                    menuItem.divider && self.$menu.append($("<li/>").addClass("divider"));
                });
                self.$menu.addClass("dropdown-menu");
                self.$toggle.append($("<b/>").addClass("caret"));
            }
            return this;
        },

        /** Add new menu item */
        _buildMenuItem: function _buildMenuItem(options) {
            var self = this;
            options = _.defaults(options || {}, {
                title: "",
                url: "",
                target: "_parent",
                noscratchbook: false
            });
            options.url = self._formatUrl(options.url);
            return $("<li/>").append($("<a/>").attr("href", options.url).attr("target", options.target).html(options.title).on("click", function(e) {
                e.preventDefault();
                self.model.set("show_menu", false);
                if (options.onclick) {
                    options.onclick();
                } else {
                    Galaxy.frame.add(options);
                }
            }));
        },

        /** Handle click event */
        _toggleClick: function _toggleClick(e) {
            var self = this;
            var model = this.model;
            e.preventDefault();
            $(".tooltip").hide();
            model.trigger("dispatch", function(m) {
                model.id !== m.id && m.get("menu") && m.set("show_menu", false);
            });
            if (!model.get("disabled")) {
                if (!model.get("menu")) {
                    model.get("onclick") ? model.get("onclick")() : Galaxy.frame.add(model.attributes);
                } else {
                    model.set("show_menu", true);
                }
            } else {
                var buildLink = function buildLink(label, url) {
                    return $("<div/>").append($("<a/>").attr("href", Galaxy.root + url).html(label)).html();
                };

                this.$toggle.popover && this.$toggle.popover("destroy");
                this.$toggle.popover({
                    html: true,
                    placement: "bottom",
                    content: "Please " + buildLink("login", "user/login?use_panels=True") + " or " + buildLink("register", "user/create?use_panels=True") + " to use this feature."
                }).popover("show");
                setTimeout(function() {
                    self.$toggle.popover("destroy");
                }, 5000);
            }
        },

        /** Url formatting */
        _formatUrl: function _formatUrl(url) {
            return typeof url == "string" && url.indexOf("//") === -1 && url.charAt(0) != "/" ? Galaxy.root + url : url;
        },

        /** body tempate */
        _template: function _template() {
            return '<ul class="nav navbar-nav">' + '<li class="dropdown">' + '<a class="dropdown-toggle"/>' + '<ul class="dropdown-menu"/>' + '<div class="dropdown-note"/>' + "</li>" + "</ul>";
        }
    });

    exports.default = {
        Collection: Collection,
        Tab: Tab
    };
});
//# sourceMappingURL=../../maps/layout/menu.js.map
