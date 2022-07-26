import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import { MastheadState, mountMasthead } from "layout/masthead";
import Panel from "layout/panel";
import Modal from "mvc/ui/ui-modal";
import Utils from "utils/utils";

const View = Backbone.View.extend({
    el: "body",
    className: "full-content",
    _panelids: ["left", "right"],

    initialize: function (options) {
        this.config = _.defaults(options.config || {}, {
            message_box_visible: false,
            message_box_content: "",
            message_box_class: "info",
            show_inactivity_warning: false,
            inactivity_box_content: "",
            hide_panels: false,
            hide_masthead: false,
        });

        // attach global objects, build mastheads
        const Galaxy = getGalaxyInstance();
        Galaxy.modal = this.modal = new Modal.View();
        Galaxy.router = this.router = options.Router && new options.Router(this, options);
        const mastheadState = new MastheadState();
        this.center = new Panel.CenterPanel();

        // display helper
        Galaxy.display = this.display = (view, noPadding) => {
            if (view.title) {
                Utils.setWindowTitle(view.title);
                view.allow_title_display = false;
            } else {
                Utils.setWindowTitle();
                view.allow_title_display = true;
            }
            if (view.active_tab) {
                this.masthead.highlight(view.active_tab);
            }
            this.center.display(view, noPadding);
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
            this.masthead = mountMasthead(this.$masthead[0], this.config, mastheadState);
        }
        this.$center.append(this.center.$el);
        this.$el.append(this.modal.$el);

        // build panels
        this.panels = {};
        if (!this.config.hide_panels) {
            _.each(this._panelids, (panel_id) => {
                const panel_class_name = panel_id.charAt(0).toUpperCase() + panel_id.slice(1);
                const panel_class = options[panel_class_name];
                if (panel_class) {
                    const panel_instance = new panel_class(this, options);
                    const panel_el = this.$(`#${panel_id}`);
                    this[panel_instance.toString()] = panel_instance;
                    this.panels[panel_id] = new Panel.SidePanel({
                        id: panel_id,
                        el: panel_el,
                        view: panel_instance,
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
                pushState: true,
            });
        }
    },

    render: function () {
        // TODO: Remove this line after select2 update
        $(".select2-hidden-accessible").remove();
        if (!this.config.hide_masthead) {
            this.renderMessageBox();
            this.renderInactivityBox();
        }
        this.renderPanels();
        return this;
    },

    /** Render message box */
    renderMessageBox: function () {
        if (this.config.message_box_visible) {
            const content = this.config.message_box_content || "";
            const level = this.config.message_box_class || "info";
            this.$messagebox
                .attr("class", `alert alert-${level} rounded-0 m-0 p-2`)
                .append($("<div/>").attr("class", "fa fa-fw mr-1 fa-exclamation"))
                .append(content)
                .toggle(!!content)
                .show();
        } else {
            this.$messagebox.hide();
        }
        return this;
    },

    /** Render inactivity warning */
    renderInactivityBox: function () {
        if (this.config.show_inactivity_warning) {
            const content = this.config.inactivity_box_content || "";
            const verificationLink = $("<a/>")
                .attr("class", "ml-1")
                .attr("href", `${getAppRoot()}user/resend_verification`)
                .text("Resend verification");
            this.$inactivebox
                .append($("<div/>").attr("class", "fa fa-fw mr-1 fa-exclamation-triangle"))
                .append(content)
                .append(verificationLink)
                .toggle(!!content)
                .show();
        } else {
            this.$inactivebox.hide();
        }
        return this;
    },

    /** Render panels */
    renderPanels: function () {
        _.each(this._panelids, (panel_id) => {
            const panel = this.panels[panel_id];
            if (panel) {
                panel.render();
            } else {
                this.$center.css(panel_id, 0);
                this.$(`#${panel_id}`).hide();
            }
        });
        return this;
    },

    /** body template */
    _template: function () {
        return [
            `<div id="everything">
                <div id="background"/>
                <div id="masthead"/>
                <small id="messagebox"/>
                <small id="inactivebox" class="alert rounded-0 m-0 p-2 alert-warning" />
                <div id="columns">
                    <div id="left" class="unified-panel"/>
                    <div id="center" />
                    <div id="right" class="unified-panel" />
                </div>
            </div>
            <div id="dd-helper" />`,
        ].join("");
    },

    toString: function () {
        return "PageLayoutView";
    },
});

export default { View: View };
