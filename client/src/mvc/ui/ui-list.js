import $ from "jquery";
import Backbone from "backbone";
import Utils from "utils/utils";
import Ui from "mvc/ui/ui-misc";
var View = Backbone.View.extend({
    initialize: function (options) {
        this.options = options;
        this.name = options.name || "element";
        this.multiple = options.multiple || false;

        // create message handler
        this.message = new Ui.Message({ cls: "col mb-0" });

        // create selections area
        this.selections = $("<div/>");

        // create select field containing the options which can be inserted into the list
        this.select = new Ui.Select.View({ optional: options.optional });

        // create insert new list element button
        this.$button = $(`<button class="fa fa-sign-in"/>`);
        this.$button.on("click", () => {
            this.add({
                id: this.select.value(),
                name: this.select.text(),
            });
        });

        // build main element
        this.setElement(this._template(options));
        this.$(".ui-list-message").append(this.message.$el);
        this.$(".ui-list-selections").append(this.selections);
        this.$(".ui-list-button").append(this.$button);
        this.$(".ui-list-select").append(this.select.$el);
    },

    /** Return/Set currently selected list elements */
    value: function (val) {
        // set new value
        if (val !== undefined) {
            this.selections.empty();
            if (Array.isArray(val)) {
                for (var i in val) {
                    var v = val[i];
                    var v_id = null;
                    var v_name = null;
                    if ($.type(v) != "string") {
                        v_id = v.id;
                        v_name = v.name;
                    } else {
                        v_id = v_name = v;
                    }
                    if (v_id != null) {
                        this.add({
                            id: v_id,
                            name: v_name,
                        });
                    }
                }
            }
            this._refresh();
        }
        // get current value
        var lst = [];
        this.$(".ui-list-id").each(function () {
            lst.push({
                id: $(this).prop("id"),
                name: $(this).find(".ui-list-name").html(),
            });
        });
        if (lst.length == 0) {
            return null;
        }
        return lst;
    },

    /** Add row */
    add: function (options) {
        var self = this;
        if (this.$(`[id="${options.id}"]`).length === 0) {
            if (!Utils.isEmpty(options.id)) {
                var $el = $(
                    this._templateRow({
                        id: options.id,
                        name: options.name,
                    })
                );
                $el.find("button").on("click", () => {
                    $el.remove();
                    self._refresh();
                });
                this.selections.append($el);
                this._refresh();
            } else {
                this.message.update({
                    message: `Please select a valid ${this.name}.`,
                    status: "danger",
                });
            }
        } else {
            this.message.update({
                message: `This ${this.name} is already in the list.`,
            });
        }
    },

    /** Update available options */
    update: function (input_def) {
        this.select.update(input_def);
    },

    /** Refresh view */
    _refresh: function () {
        if (this.$(".ui-list-id").length > 0) {
            !this.multiple && this.$button.attr("disabled", true);
        } else {
            this.$button.attr("disabled", false);
        }
        this.options.onchange && this.options.onchange();
    },

    /** Main Template */
    _template: function (options) {
        return `<div class="ui-list container">
                    <div class="row">
                        <div class="col-1 pl-0 mb-2">
                            <div class="ui-list-button"/>
                        </div>
                        <div class="ui-list-select col pr-0"/>
                    </div>
                    <div class="ui-list-message mt-2 row"/>
                    <div class="ui-list-selections mt-2"/>
                </div>`;
    },

    /** Row Template */
    _templateRow: function (options) {
        return `<div id="${options.id}" class="ui-list-id row mt-2">
                    <button class="ui-list-delete fa fa-trash mr-3"/>
                    <div class="ui-list-name">${options.name}</span>
                </div>`;
    },
});

export default {
    View: View,
};
