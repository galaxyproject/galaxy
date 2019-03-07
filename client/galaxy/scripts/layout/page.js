import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import Data from "layout/data";
import Masthead from "layout/masthead";
import Panel from "layout/panel";
import Modal from "mvc/ui/ui-modal";
import Utils from "utils/utils";

var View = Backbone.View.extend({
    el: "body",
    className: "full-content",
    _panelids: ["left", "right"],

    initialize: function(options) {
        var self = this;
        this.config = _.defaults(options.config || {}, {
            message_box_visible: false,
            message_box_content: "",
            message_box_class: "info",
            show_inactivity_warning: false,
            inactivity_box_content: "",
            hide_panels: false,
            hide_masthead: false
        });

        // attach global objects, build mastheads
        let Galaxy = getGalaxyInstance();
        Galaxy.modal = this.modal = new Modal.View();
        Galaxy.router = this.router = options.Router && new options.Router(self, options);
        Galaxy.data = this.data = new Data(this);
        this.masthead = new Masthead.View(this.config);
        this.center = new Panel.CenterPanel();

        // display helper
        Galaxy.display = this.display = view => {
            if (view.title) {
                Utils.setWindowTitle(view.title);
                view.allow_title_display = false;
            } else {
                Utils.setWindowTitle();
                view.allow_title_display = true;
            }
            if (view.active_tab) {
                self.masthead.highlight(view.active_tab);
            }
            self.center.display(view);
        };

        // build page template
        this.$el.attr("scroll", "no");
        this.$el.html(this._template());
        this.$masthead = this.$("#masthead");
        this.$center = this.$("#center");
        this.$messagebox = this.$("#messagebox");
        this.$inactivebox = this.$("#inactivebox");

        // build components
        if (this.config.hide_masthead) {
            this.$masthead.remove();
            this.$center.css("top", 0);
        } else {
            this.$masthead.replaceWith(this.masthead.$el);
        }
        this.$center.append(this.center.$el);
        this.$el.append(this.masthead.frame.$el);
        this.$el.append(this.modal.$el);

        // build panels
        this.panels = {};
        if (!this.config.hide_panels) {
            _.each(this._panelids, panel_id => {
                var panel_class_name = panel_id.charAt(0).toUpperCase() + panel_id.slice(1);
                var panel_class = options[panel_class_name];
                if (panel_class) {
                    var panel_instance = new panel_class(self, options);
                    var panel_el = self.$(`#${panel_id}`);
                    self[panel_instance.toString()] = panel_instance;
                    self.panels[panel_id] = new Panel.SidePanel({
                        id: panel_id,
                        el: panel_el,
                        view: panel_instance
                    });
                    if (this.config.hide_masthead) {
                        panel_el.css("top", 0);
                    }
                }
            });
        }
        this.render();

        // start the router
        if (this.router) {
            Backbone.history.start({
                root: getAppRoot(),
                pushState: true
            });
        }
    },

    render: function() {
        // TODO: Remove this line after select2 update
        $(".select2-hidden-accessible").remove();
        if (!this.config.hide_masthead) {
            this.masthead.render();
            this.renderMessageBox();
            this.renderInactivityBox();
        }
        this.renderPanels();
        this._checkCommunicationServerOnline();
        return this;
    },

    /** Render message box */
    renderMessageBox: function() {
        if (this.config.message_box_visible) {
            var content = this.config.message_box_content || "";
            var level = this.config.message_box_class || "info";
            this.$el.addClass("has-message-box");
            this.$messagebox
                .attr("class", `panel-${level}-message`)
                .html(content)
                .toggle(!!content)
                .show();
        } else {
            this.$el.removeClass("has-message-box");
            this.$messagebox.hide();
        }
        return this;
    },

    /** Render inactivity warning */
    renderInactivityBox: function() {
        if (this.config.show_inactivity_warning) {
            var content = this.config.inactivity_box_content || "";
            var verificationLink = $("<a/>")
                .attr("href", `${getAppRoot()}user/resend_verification`)
                .text("Resend verification");
            this.$el.addClass("has-inactivity-box");
            this.$inactivebox
                .html(`${content} `)
                .append(verificationLink)
                .toggle(!!content)
                .show();
        } else {
            this.$el.removeClass("has-inactivity-box");
            this.$inactivebox.hide();
        }
        return this;
    },

    /** Render panels */
    renderPanels: function() {
        var self = this;
        _.each(this._panelids, panel_id => {
            var panel = self.panels[panel_id];
            if (panel) {
                panel.render();
            } else {
                self.$center.css(panel_id, 0);
                self.$(`#${panel_id}`).hide();
            }
        });
        return this;
    },

    /** body template */
    _template: function() {
        return [
            `<div id="everything">
                <div id="background"/>
                <div id="masthead"/>
                <div id="messagebox"/>
                <div id="inactivebox" class="panel-warning-message" />
                <div id="columns">
                    <div id="left" class="unified-panel"/>
                    <div id="center" />
                    <div id="right" class="unified-panel" />
                </div>
            </div>
            <div id="dd-helper" />`
        ].join("");
    },

    toString: function() {
        return "PageLayoutView";
    },

    /** Check if the communication server is online and show the icon otherwise hide the icon */
    _checkCommunicationServerOnline: function() {
        let Galaxy = getGalaxyInstance();
        var host = Galaxy.config.communication_server_host;
        var port = Galaxy.config.communication_server_port;
        var preferences = Galaxy.user.attributes.preferences;
        var $chat_icon_element = $("#show-chat-online");
        /** Check if the user has deactivated the communication in it's personal settings */
        if (preferences && ["1", "true"].indexOf(preferences.communication_server) != -1) {
            // See if the configured communication server is available
            $.ajax({
                url: `${host}:${port}`
            })
                .success(data => {
                    // enable communication only when a user is logged in
                    if (Galaxy.user.id !== null) {
                        if ($chat_icon_element.css("visibility") === "hidden") {
                            $chat_icon_element.css("visibility", "visible");
                        }
                    }
                })
                .error(data => {
                    // hide the communication icon if the communication server is not available
                    $chat_icon_element.css("visibility", "hidden");
                });
        } else {
            $chat_icon_element.css("visibility", "hidden");
        }
    }
});

export default { View: View };
