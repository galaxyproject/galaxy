/** This class creates a ui component which enables the dynamic creation of portlets */
import Backbone from "backbone";
import $ from "jquery";
import _ from "underscore";
import _l from "utils/localization";
import Utils from "utils/utils";

import Ui from "./misc";
import Portlet from "./portlet";

export var View = Backbone.View.extend({
    initialize: function (options) {
        this.list = {};
        this.options = Utils.merge(options, {
            title: _l("Repeat"),
            empty_text: "Not available.",
            max: null,
            min: null,
        });
        this.button_new = new Ui.Button({
            icon: "fa-plus",
            title: `Insert ${this.options.title}`,
            tooltip: `Add new ${this.options.title} block`,
            cls: "btn btn-secondary float-none form-repeat-add",
            onclick: function () {
                if (options.onnew) {
                    options.onnew();
                }
            },
        });
        this.setElement(
            $("<div/>")
                .append((this.$list = $("<div/>")))
                .append($("<div/>").append(this.button_new.$el))
        );
    },

    /** Number of repeat blocks */
    size: function () {
        return _.size(this.list);
    },

    /** Add new repeat block */
    add: function (options) {
        if (!options.id || this.list[options.id]) {
            console.debug("form-repeat::add()", "Duplicate or invalid repeat block id.");
            return;
        }
        var button_delete = new Ui.Button({
            icon: "fa-trash-o",
            tooltip: _l("Delete this repeat block"),
            cls: "ui-button-icon-plain form-repeat-delete",
            onclick: function () {
                if (options.ondel) {
                    options.ondel();
                }
            },
        });
        var portlet = new Portlet.View({
            id: options.id,
            title: _l("placeholder"),
            cls: options.cls || "ui-portlet-section",
            operations: { button_delete: button_delete },
        });
        portlet.append(options.$el);
        portlet.$el.addClass("section-row").hide();
        this.list[options.id] = portlet;
        this.$list.append(portlet.$el.fadeIn("fast"));
        if (this.options.max > 0 && this.size() >= this.options.max) {
            this.button_new.disable();
        }
        this._refresh();
    },

    /** Delete repeat block */
    del: function (id) {
        if (!this.list[id]) {
            console.debug("form-repeat::del()", "Invalid repeat block id.");
            return;
        }
        this.$list.find(`#${id}`).remove();
        delete this.list[id];
        this.button_new.enable();
        this._refresh();
    },

    /** Remove all */
    delAll: function () {
        for (var id in this.list) {
            this.del(id);
        }
    },

    /** Hides add/del options */
    hideOptions: function () {
        this.button_new.$el.hide();
        _.each(this.list, (portlet) => {
            portlet.hideOperation("button_delete");
        });
        if (_.isEmpty(this.list)) {
            this.$el.append($("<div/>").addClass("form-text text-muted").html(this.options.empty_text));
        }
    },

    /** Refresh view */
    _refresh: function () {
        var index = 0;
        for (var id in this.list) {
            var portlet = this.list[id];
            portlet.title(`${++index}: ${this.options.title}`);
            portlet[this.size() > this.options.min ? "showOperation" : "hideOperation"]("button_delete");
        }
    },
});

export default {
    View: View,
};
