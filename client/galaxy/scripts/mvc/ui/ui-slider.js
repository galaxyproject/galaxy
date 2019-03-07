import $ from "jquery";
import Backbone from "backbone";

import Utils from "utils/utils";

var View = Backbone.View.extend({
    initialize: function(options) {
        var self = this;
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
                onchange: function() {}
            }).set(options);

        // create new element
        this.setElement(this._template());
        this.$el.attr("id", this.model.id);
        this.$text = this.$(".ui-form-slider-text");
        this.$slider = this.$(".ui-form-slider-element");

        // add text field event
        var pressed = [];
        this.$text
            .on("change", function() {
                self.value($(this).val());
            })
            .on("keyup", e => {
                pressed[e.which] = false;
            })
            .on("keydown", function(e) {
                var v = e.which;
                pressed[v] = true;
                if (self.model.get("is_workflow") && pressed[16] && v == 52) {
                    self.value("$");
                    event.preventDefault();
                } else if (
                    !(
                        v == 8 ||
                        v == 9 ||
                        v == 13 ||
                        v == 37 ||
                        v == 39 ||
                        (v >= 48 && v <= 57) ||
                        (v >= 96 && v <= 105) ||
                        ((v == 190 || v == 110) &&
                            $(this)
                                .val()
                                .indexOf(".") == -1 &&
                            self.model.get("precise")) ||
                        ((v == 189 || v == 109) &&
                            $(this)
                                .val()
                                .indexOf("-") == -1) ||
                        self._isParameter($(this).val()) ||
                        pressed[91] ||
                        pressed[17]
                    )
                ) {
                    event.preventDefault();
                }
            });

        // build slider, cannot be rebuild in render
        var opts = this.model.attributes;
        this.has_slider = opts.max !== null && opts.min !== null && opts.max > opts.min;
        var step = opts.step;
        if (!step) {
            if (opts.precise && this.has_slider) {
                step = (opts.max - opts.min) / opts.split;
            } else {
                step = 1.0;
            }
        }
        if (this.has_slider) {
            this.$slider.slider({ min: opts.min, max: opts.max, step: step }).on("slide", (event, ui) => {
                self.value(ui.value);
            });
        }

        // add listeners
        this.listenTo(this.model, "change", this.render, this);
        this.render();
    },

    render: function() {
        var value = this.model.get("value");
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
    value: function(new_val) {
        if (new_val !== undefined) {
            let options = this.model.attributes;
            let original_val = new_val;
            let is_value = new_val !== null && new_val !== "" && !this._isParameter(new_val);
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
            let has_changed = is_value && parseInt(original_val) !== parseInt(new_val);
            let message = has_changed ? "This value was invalid or out-of-range. It has been auto-corrected." : null;
            this.model.trigger("error", message);
        }
        return this.model.get("value");
    },

    /** Return true if the field contains a workflow parameter i.e. $('name') */
    _isParameter: function(value) {
        return this.model.get("is_workflow") && String(value).substring(0, 1) === "$";
    },

    /** Slider template */
    _template: function() {
        return `<div class="ui-form-slider container-fluid">
                    <div class="row">
                        <input class="ui-input ui-form-slider-text" type="text"/>
                        <div class="ui-form-slider-element col mt-1"/>
                    </div>
                </div>`;
    }
});

export default {
    View: View
};
