import Backbone from "backbone";
import { filesDialog } from "utils/data";
import _l from "utils/localization";
import Ui from "mvc/ui/ui-misc";

var View = Backbone.View.extend({
    initialize: function (options) {
        this.model = new Backbone.Model();
        this.target = options.target;
        const props = {
            mode: "directory",
            requireWritable: true,
        };
        // create insert edit button
        this.browse_button = new Ui.Button({
            title: _l("Select"),
            icon: "fa fa-edit",
            tooltip: _l("Select URI"),
            onclick: () => {
                filesDialog((uri) => {
                    this._handleRemoteFilesUri(uri);
                }, props);
            },
        });

        // add change event. fires on trigger
        this.on("change", () => {
            if (options.onchange) {
                options.onchange(this.value());
            }
        });

        // create elements
        this.setElement(this._template(options));
        this.$text = this.$(".ui-uri-preview");
        this.$(".ui-file-select-button").append(this.browse_button.$el);
        this.listenTo(this.model, "change", this.render, this);
        this.render();
    },

    _handleRemoteFilesUri: function (uri) {
        this._setValue(uri);
    },

    render: function () {
        const value = this._value;
        if (value) {
            if (typeof value == "string") {
                this.$text.text(value);
            } else if (value.url !== this.$text.text()) {
                this.$text.text(value.url);
            }
        } else {
            this.$text.text("select...");
        }
    },

    /** Main Template */
    _template: function (options) {
        return `
            <div class="ui-rules-edit clearfix">
                <span class="ui-uri-preview" />
                <span class="ui-file-select-button float-left" />
            </div>
        `;
    },

    /** Return/Set current value */
    value: function (new_value) {
        if (new_value !== undefined) {
            this._setValue(new_value);
        } else {
            return this._getValue();
        }
    },

    /** Update input element options */
    update: function (input_def) {
        this.target = input_def.target;
    },

    /** Returns current value */
    _getValue: function () {
        return this._value?.url;
    },

    /** Sets current value */
    _setValue: function (new_value) {
        if (new_value) {
            if (typeof new_value == "string") {
                let parsed_value;
                // if new_value is not a JSON, set it as String
                try {
                    parsed_value = JSON.parse(new_value);
                } catch (e) {
                    parsed_value = new_value;
                } finally {
                    new_value = parsed_value;
                }
            }
            this._value = new_value;
            this.model.trigger("error", null);
            this.model.trigger("change");
            this.trigger("change");
        }
    },
});

export default {
    View: View,
};
