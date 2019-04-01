import Backbone from "backbone";
import _ from "underscore";
import Utils from "utils/utils";
/**
 * A plugin for initializing select2 input items.
 * Make sure the select2 library itself is loaded beforehand.
 * Also the element to which select2 will be appended has to
 * be created before select2 initialization (and passed as option).
 */
var View = Backbone.View.extend({
    // options
    optionsDefault: {
        css: "",
        placeholder: "No data available",
        data: [],
        value: null,
        multiple: false,
        minimumInputLength: 0,
        maximumTextLength: 100,
        // example format of initial data: "id:name,55:anotherrole@role.com,27:role@role.com"
        initialData: ""
    },

    // initialize
    initialize: function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);

        // create new element
        this.setElement(this._template(this.options));

        // check if container exists
        if (!this.options.container) {
            console.log("ui-select::initialize() : container not specified.");
            return;
        }

        // add to dom
        this.options.container.append(this.$el);

        // link selection dictionary
        this.select_data = this.options.data;

        // refresh
        this._refresh();

        if (!this.options.multiple) {
            // initial value
            if (this.options.value) {
                this._setValue(this.options.value);
            }

            // add change event
            var self = this;
            if (this.options.onchange) {
                this.$el.on("change", () => {
                    self.options.onchange(self.value());
                });
            }
        }
    },

    // value
    value: function(new_value) {
        // get current id/value
        var before = this._getValue();

        // check if new_value is defined
        if (new_value !== undefined) {
            this._setValue(new_value);
        }

        // get current id/value
        var after = this._getValue();

        // fire onchange
        if (after != before && this.options.onchange) {
            this.options.onchange(after);
        }

        // return current value
        return after;
    },

    // label
    text: function() {
        return this.$el.select2("data").text;
    },

    // disabled
    disabled: function() {
        return !this.$el.select2("enable");
    },

    // enable
    enable: function() {
        this.$el.select2("enable", true);
    },

    // disable
    disable: function() {
        this.$el.select2("enable", false);
    },

    // add
    add: function(options) {
        // add options
        this.select_data.push({
            id: options.id,
            text: options.text
        });

        // refresh
        this._refresh();
    },

    // remove
    del: function(id) {
        // search option
        var index = this._getIndex(id);

        // check if found
        if (index != -1) {
            // remove options
            this.select_data.splice(index, 1);

            // refresh
            this._refresh();
        }
    },

    // remove
    remove: function() {
        this.$el.select2("destroy");
    },

    // update
    update: function(options) {
        // copy options
        this.select_data = [];
        for (var key in options.data) {
            this.select_data.push(options.data[key]);
        }

        // refresh
        this._refresh();
    },

    // refresh
    _refresh: function() {
        let select_opt;
        // add select2 data based on type of input
        if (!this.options.multiple) {
            if (this.select_data) {
                this.select_data.map(value => {
                    let mx = this.options.maximumTextLength + 3;
                    if (value.text && value.text.length > mx) {
                        let pos = value.text.indexOf(`(${value.id})`);
                        pos = pos != -1 && pos < mx ? pos : mx;
                        let sub = value.text.substring(0, pos).replace(/[ .]*$/, "");
                        value.text = `${sub}...(${value.id})`;
                    }
                });
            }
            var selected = this._getValue();
            select_opt = {
                data: this.select_data,
                containerCssClass: this.options.css,
                placeholder: this.options.placeholder,
                dropdownAutoWidth: true
            };
            this.$el.select2(select_opt);
            // select previous value (if exists)
            this._setValue(selected);
        } else {
            select_opt = {
                multiple: this.options.multiple,
                containerCssClass: this.options.css,
                placeholder: this.options.placeholder,
                minimumInputLength: this.options.minimumInputLength,
                ajax: this.options.ajax,
                dropdownCssClass: this.options.dropdownCssClass,
                escapeMarkup: this.options.escapeMarkup,
                formatResult: this.options.formatResult,
                formatSelection: this.options.formatSelection,
                initSelection: this.options.initSelection,
                initialData: this.options.initialData
            };
            this.$el.select2(select_opt);
        }
    },

    // get index
    _getIndex: function(value) {
        // returns the index of the searched value
        _.findIndex(this.select_data, { id: value });
    },

    // get value
    _getValue: function() {
        return this.$el.select2("val");
    },

    // set value
    _setValue: function(new_value) {
        var index = this._getIndex(new_value);
        if (index == -1) {
            if (this.select_data.length > 0) {
                new_value = this.select_data[0].id;
            }
        }
        this.$el.select2("val", new_value);
    },

    // element
    _template: function(options) {
        return `<input type="hidden" value="${this.options.initialData}"/>`;
    }
});

export default {
    View: View
};
