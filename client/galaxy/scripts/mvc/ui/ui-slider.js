import Backbone from "backbone";
import IMask from "imask";

import Utils from "utils/utils";

const View = Backbone.View.extend({
    initialize: function (options) {
        this.model =
            (options && options.model) ||
            new Backbone.Model({
                id: Utils.uid(),
                min: null,
                max: null,
                step: null,
                precise: false,
                split: 10000,
                value: null,
                onchange: function () {},
            }).set(options);

        // create new element
        this.setElement(this._template());
        this.$el.attr("id", this.model.id);
        this.$text = this.$(".ui-form-slider-text");
        this.$slider = this.$(".ui-form-slider-element");

        IMask(this.$text[0], {
            mask: (value) => {
                if (this._isParameter(value)) {
                    return true;
                }
                if (!this.model.get("precise")) {
                    if (value != value.split(".")[0]) {
                        return false;
                    }
                }
                return value == value.replace(/[^0-9eE.-]/g, "");
            },
        });

        this.$text[0].addEventListener("change", (e) => {
            this.value(e.currentTarget.value);
        });

        // build slider, cannot be rebuild in render
        const opts = this.model.attributes;
        this.has_slider = opts.max !== null && opts.min !== null && opts.max > opts.min;
        let step = opts.step;
        if (!step) {
            if (opts.precise && this.has_slider) {
                step = (opts.max - opts.min) / opts.split;
            } else {
                step = 1.0;
            }
        }
        if (this.has_slider) {
            this.$slider.slider({ min: opts.min, max: opts.max, step: step }).on("slide", (event, ui) => {
                this.value(ui.value);
            });
        }

        // add listeners
        this.listenTo(this.model, "change", this.render, this);
        this.render();
    },

    render: function () {
        const value = this.model.get("value");
        if (this.has_slider) {
            this.$slider.slider("value", value);
            this.$slider.show();
            this.$text.addClass("col-3 mr-3");
        } else {
            this.$slider.hide();
            this.$text.removeClass("col-3 mr-3");
        }
        if (value !== this.$text.val()) {
            this.$text.val(value);
        }
    },

    /** Set and return the current value */
    value: function (new_val) {
        if (new_val !== undefined) {
            const options = this.model.attributes;
            const original_val = new_val;
            const is_value = new_val !== null && new_val !== "" && !this._isParameter(new_val);
            if (is_value) {
                if (isNaN(new_val)) {
                    new_val = 0;
                }
                if (!options.precise) {
                    new_val = Math.round(new_val);
                }
                if (options.max !== null && !isNaN(options.max)) {
                    new_val = Math.min(new_val, options.max);
                }
                if (options.min !== null && !isNaN(options.min)) {
                    new_val = Math.max(new_val, options.min);
                }
            }
            this.model.set("value", new_val);
            this.model.trigger("change");
            options.onchange(new_val);
            const has_changed = is_value && parseInt(original_val) !== parseInt(new_val);
            const message = has_changed ? "This value was invalid or out-of-range. It has been auto-corrected." : null;
            this.model.trigger("error", message);
        }
        return this.model.get("value");
    },

    /** Return true if the field contains a workflow parameter i.e. $('name') */
    _isParameter: function (value) {
        return this.model.get("is_workflow") && String(value).substring(0, 1) === "$";
    },

    /** Slider template */
    _template: function () {
        return `<div class="ui-form-slider container-fluid">
                    <div class="row">
                        <input class="ui-input ui-form-slider-text" type="text"/>
                        <div class="ui-form-slider-element col mt-1"/>
                    </div>
                </div>`;
    },
});

export default {
    View: View,
};
