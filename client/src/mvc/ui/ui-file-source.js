import Backbone from "backbone";
import { breadcrump } from "utils/mountBreadcrump";

var View = Backbone.View.extend({
    initialize: function (options) {
        this.model = new Backbone.Model();
        this.target = options.target;

        // add change event. fires on trigger
        this.on("change", () => {
            if (options.onchange) {
                options.onchange(this.value());
            }
        });

        // create elements
        this.setElement(this._template(options));
        this.listenTo(this.model, "change", this.render, this);
        this.render();
    },

    _handleRemoteFilesUri: function (uri) {
        this._setValue(uri);
    },

    render: function () {
        let value = this._value;
        if (value && typeof value != "string") {
            value = value.url;
        }
        if (!value) {
            value = "";
        }
        breadcrump(
            ".ui-uri-preview",
            (uri) => {
                this._handleRemoteFilesUri(uri);
            },

            { url: value }
        );
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
        return this._value;
    },

    /** Sets current value */
    _setValue: function (new_value) {
        this._value = new_value;
        this.model.trigger("error", null);
        this.model.trigger("change");
        this.trigger("change");
    },
});

export default {
    View: View,
};
