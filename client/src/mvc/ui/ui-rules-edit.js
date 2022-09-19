import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import _l from "utils/localization";
import Ui from "mvc/ui/ui-misc";
import Vue from "vue";
import RuleBasedCollectionCreatorModal from "components/Collections/RuleBasedCollectionCreatorModal";
import { RulesDisplay } from "components/RulesDisplay";

/**
 * Bridge rule based builder and the tool form.
 */
var View = Backbone.View.extend({
    initialize: function (options) {
        this.model = new Backbone.Model();
        this.target = options.target;
        const view = this;

        // create insert edit button
        this.browse_button = new Ui.Button({
            title: _l("Edit"),
            icon: "fa fa-edit",
            tooltip: _l("Edit Rules"),
            onclick: () => {
                if (view.target) {
                    view._fetchCollectionAndEdit();
                } else {
                    view._showRuleEditor(null);
                }
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
        this.$(".ui-rules-edit-button").append(this.browse_button.$el);
        var rulesDisplayInstance = Vue.extend(RulesDisplay);
        var vm = document.createElement("div");
        this.$(".ui-rules-preview").append(vm);
        this.instance = new rulesDisplayInstance({
            propsData: {
                initialRules: {
                    rules: [],
                    mapping: [],
                },
            },
        });
        this.instance.$mount(vm);
    },

    _fetchCollectionAndEdit: function () {
        const view = this;
        const url = `${getAppRoot()}api/dataset_collections/${view.target.id}?instance_type=history`;
        axios
            .get(url)
            .then((response) => this._showCollection(response))
            .catch(view._renderFetchError);
    },

    _showCollection: function (response) {
        const elements = response.data;
        this._showRuleEditor(elements);
    },

    _showRuleEditor: function (elements) {
        const elementsType = "collection_contents";
        const importType = "collections";
        const value = this._value;
        const options = {
            saveRulesFn: (rules) => this._handleRulesSave(rules),
            initialRules: value,
        };
        RuleBasedCollectionCreatorModal.ruleBasedCollectionCreatorModal(
            elements,
            elementsType,
            importType,
            options
        ).catch(() => {});
    },

    _handleRulesSave: function (rules) {
        this._setValue(rules);
    },

    _renderFetchError: function (e) {
        console.log(e);
        console.log("problem fetching collection");
    },

    /** Main Template */
    _template: function (options) {
        return `
            <div class="ui-rules-edit clearfix">
                <span class="ui-rules-preview" />
                <span class="ui-rules-edit-button float-left" />
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
        if (new_value) {
            if (typeof new_value == "string") {
                new_value = JSON.parse(new_value);
            }
            this._value = new_value;
            this.model.trigger("error", null);
            this.trigger("change");
            this.instance.inputRules = new_value;
        }
    },
});

export default {
    View: View,
};
