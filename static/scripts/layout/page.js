define("layout/page", ["exports", "layout/masthead", "layout/panel", "mvc/ui/ui-modal", "utils/utils"], function(exports, _masthead, _panel, _uiModal, _utils) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _masthead2 = _interopRequireDefault(_masthead);

    var _panel2 = _interopRequireDefault(_panel);

    var _uiModal2 = _interopRequireDefault(_uiModal);

    var _utils2 = _interopRequireDefault(_utils);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    var View = Backbone.View.extend({
        el: "body",
        className: "full-content",
        _panelids: ["left", "right"],

        initialize: function initialize(options) {
            var self = this;
            this.config = _.defaults(options.config || {}, {
                message_box_visible: false,
                message_box_content: "",
                message_box_class: "info",
                show_inactivity_warning: false,
                inactivity_box_content: ""
            });

            // attach global objects, build mastheads
            Galaxy.modal = this.modal = new _uiModal2.default.View();
            Galaxy.display = this.display = function(view) {
                if (view.title) {
                    _utils2.default.setWindowTitle(view.title);
                    view.allow_title_display = false;
                } else {
                    _utils2.default.setWindowTitle();
                    view.allow_title_display = true;
                }
                self.center.display(view);
            };
            Galaxy.router = this.router = options.Router && new options.Router(self, options);
            this.masthead = new _masthead2.default.View(this.config);
            this.center = new _panel2.default.CenterPanel();

            // build page template
            this.$el.attr("scroll", "no");
            this.$el.html(this._template());
            this.$("#masthead").replaceWith(this.masthead.$el);
            this.$("#center").append(this.center.$el);
            this.$el.append(this.masthead.frame.$el);
            this.$el.append(this.modal.$el);
            this.$messagebox = this.$("#messagebox");
            this.$inactivebox = this.$("#inactivebox");

            // build panels
            this.panels = {};
            _.each(this._panelids, function(panel_id) {
                var panel_class_name = panel_id.charAt(0).toUpperCase() + panel_id.slice(1);
                var panel_class = options[panel_class_name];
                if (panel_class) {
                    var panel_instance = new panel_class(self, options);
                    self[panel_instance.toString()] = panel_instance;
                    self.panels[panel_id] = new _panel2.default.SidePanel({
                        id: panel_id,
                        el: self.$("#" + panel_id),
                        view: panel_instance
                    });
                }
            });
            this.render();

            // start the router
            this.router && Backbone.history.start({
                root: Galaxy.root,
                pushState: true
            });
        },

        render: function render() {
            // TODO: Remove this line after select2 update
            $(".select2-hidden-accessible").remove();
            this.masthead.render();
            this.renderMessageBox();
            this.renderInactivityBox();
            this.renderPanels();
            this._checkCommunicationServerOnline();
            return this;
        },

        /** Render message box */
        renderMessageBox: function renderMessageBox() {
            if (this.config.message_box_visible) {
                var content = this.config.message_box_content || "";
                var level = this.config.message_box_class || "info";
                this.$el.addClass("has-message-box");
                this.$messagebox.attr("class", "panel-" + level + "-message").html(content).toggle(!!content).show();
            } else {
                this.$el.removeClass("has-message-box");
                this.$messagebox.hide();
            }
            return this;
        },

        /** Render inactivity warning */
        renderInactivityBox: function renderInactivityBox() {
            if (this.config.show_inactivity_warning) {
                var content = this.config.inactivity_box_content || "";
                var verificationLink = $("<a/>").attr("href", Galaxy.root + "user/resend_verification").text("Resend verification");
                this.$el.addClass("has-inactivity-box");
                this.$inactivebox.html(content + " ").append(verificationLink).toggle(!!content).show();
            } else {
                this.$el.removeClass("has-inactivity-box");
                this.$inactivebox.hide();
            }
            return this;
        },

        /** Render panels */
        renderPanels: function renderPanels() {
            var self = this;
            _.each(this._panelids, function(panel_id) {
                var panel = self.panels[panel_id];
                if (panel) {
                    panel.render();
                } else {
                    self.$("#center").css(panel_id, 0);
                    self.$("#" + panel_id).hide();
                }
            });
            return this;
        },

        /** body template */
        _template: function _template() {
            return ['<div id="everything">', '<div id="background"/>', '<div id="masthead"/>', '<div id="messagebox"/>', '<div id="inactivebox" class="panel-warning-message" />', '<div id="left" />', '<div id="center" />', '<div id="right" />', "</div>", '<div id="dd-helper" />'].join("");
        },

        toString: function toString() {
            return "PageLayoutView";
        },

        /** Check if the communication server is online and show the icon otherwise hide the icon */
        _checkCommunicationServerOnline: function _checkCommunicationServerOnline() {
            var host = window.Galaxy.config.communication_server_host;
            var port = window.Galaxy.config.communication_server_port;
            var preferences = window.Galaxy.user.attributes.preferences;
            var $chat_icon_element = $("#show-chat-online");
            /** Check if the user has deactivated the communication in it's personal settings */
            if (preferences && ["1", "true"].indexOf(preferences.communication_server) != -1) {
                // See if the configured communication server is available
                $.ajax({
                    url: host + ":" + port
                }).success(function(data) {
                    // enable communication only when a user is logged in
                    if (window.Galaxy.user.id !== null) {
                        if ($chat_icon_element.css("visibility") === "hidden") {
                            $chat_icon_element.css("visibility", "visible");
                        }
                    }
                }).error(function(data) {
                    // hide the communication icon if the communication server is not available
                    $chat_icon_element.css("visibility", "hidden");
                });
            } else {
                $chat_icon_element.css("visibility", "hidden");
            }
        }
    });

    exports.default = {
        View: View
    };
});
//# sourceMappingURL=../../maps/layout/page.js.map
