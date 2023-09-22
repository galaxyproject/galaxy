/**
 * Model, view, and controller objects for Galaxy tools in Trackster.
 */
import _ from "underscore";
import $ from "jquery";
import * as d3 from "d3v3";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import util from "viz/trackster/util";
import { DatasetCollection } from "mvc/dataset/data";

/**
 * Mixin for tracking model visibility.
 */
var VisibilityMixin = {
    hidden: false,

    show: function () {
        this.set("hidden", false);
    },

    hide: function () {
        this.set("hidden", true);
    },

    toggle: function () {
        this.set("hidden", !this.get("hidden"));
    },

    is_visible: function () {
        return !this.attributes.hidden;
    },
};

/**
 * A tool parameter.
 */
var ToolParameter = Backbone.Model.extend({
    defaults: {
        name: null,
        label: null,
        type: null,
        value: null,
        html: null,
        num_samples: 5,
    },

    initialize: function (options) {
        this.attributes.html = unescape(this.attributes.html);
    },

    copy: function () {
        return new ToolParameter(this.toJSON());
    },

    set_value: function (value) {
        this.set("value", value || "");
    },
});

var ToolParameterCollection = Backbone.Collection.extend({
    model: ToolParameter,
});

/**
 * A data tool parameter.
 */
var DataToolParameter = ToolParameter.extend({});

/**
 * An integer tool parameter.
 */
var IntegerToolParameter = ToolParameter.extend({
    set_value: function (value) {
        this.set("value", parseInt(value, 10));
    },

    /**
     * Returns samples from a tool input.
     */
    get_samples: function () {
        return d3.scale
            .linear()
            .domain([this.get("min"), this.get("max")])
            .ticks(this.get("num_samples"));
    },
});

var FloatToolParameter = IntegerToolParameter.extend({
    set_value: function (value) {
        this.set("value", parseFloat(value));
    },
});

/**
 * A select tool parameter.
 */
var SelectToolParameter = ToolParameter.extend({
    /**
     * Returns tool options.
     */
    get_samples: function () {
        return _.map(this.get("options"), (option) => option[0]);
    },
});

// Set up dictionary of parameter types.
ToolParameter.subModelTypes = {
    integer: IntegerToolParameter,
    float: FloatToolParameter,
    data: DataToolParameter,
    select: SelectToolParameter,
};

/**
 * A Galaxy tool.
 */
var Tool = Backbone.Model.extend({
    // Default attributes.
    defaults: {
        id: null,
        name: null,
        description: null,
        target: null,
        inputs: [],
        outputs: [],
    },

    urlRoot: `${getAppRoot()}api/tools`,

    initialize: function (options) {
        // Set parameters.
        this.set(
            "inputs",
            new ToolParameterCollection(
                _.map(options.inputs, (p) => {
                    var p_class = ToolParameter.subModelTypes[p.type] || ToolParameter;
                    return new p_class(p);
                })
            )
        );
    },

    /**
     *
     */
    toJSON: function () {
        var rval = Backbone.Model.prototype.toJSON.call(this);

        // Convert inputs to JSON manually.
        rval.inputs = this.get("inputs").map((i) => i.toJSON());
        return rval;
    },

    /**
     * Removes inputs of a particular type; this is useful because not all inputs can be handled by
     * client and server yet.
     */
    remove_inputs: function (types) {
        var tool = this;

        var incompatible_inputs = tool.get("inputs").filter((input) => types.indexOf(input.get("type")) !== -1);

        tool.get("inputs").remove(incompatible_inputs);
    },

    /**
     * Returns object copy, optionally including only inputs that can be sampled.
     */
    copy: function (only_samplable_inputs) {
        var copy = new Tool(this.toJSON());

        // Return only samplable inputs if flag is set.
        if (only_samplable_inputs) {
            var valid_inputs = new Backbone.Collection();
            copy.get("inputs").each((input) => {
                if (input.get_samples()) {
                    valid_inputs.push(input);
                }
            });
            copy.set("inputs", valid_inputs);
        }

        return copy;
    },

    apply_search_results: function (results) {
        _.indexOf(results, this.attributes.id) !== -1 ? this.show() : this.hide();
        return this.is_visible();
    },

    /**
     * Set a tool input's value.
     */
    set_input_value: function (name, value) {
        this.get("inputs")
            .find((input) => input.get("name") === name)
            .set("value", value);
    },

    /**
     * Set many input values at once.
     */
    set_input_values: function (inputs_dict) {
        var self = this;
        _.each(_.keys(inputs_dict), (input_name) => {
            self.set_input_value(input_name, inputs_dict[input_name]);
        });
    },

    /**
     * Run tool; returns a Deferred that resolves to the tool's output(s).
     */
    run: function () {
        return this._run();
    },

    /**
     * Rerun tool using regions and a target dataset.
     */
    rerun: function (target_dataset, regions) {
        return this._run({
            action: "rerun",
            target_dataset_id: target_dataset.id,
            regions: regions,
        });
    },

    /**
     * Returns input dict for tool's inputs.
     */
    get_inputs_dict: function () {
        var input_dict = {};
        this.get("inputs").each((input) => {
            input_dict[input.get("name")] = input.get("value");
        });
        return input_dict;
    },

    /**
     * Run tool; returns a Deferred that resolves to the tool's output(s).
     * NOTE: this method is a helper method and should not be called directly.
     */
    _run: function (additional_params) {
        // Create payload.
        var payload = _.extend(
            {
                tool_id: this.id,
                inputs: this.get_inputs_dict(),
            },
            additional_params
        );

        // Because job may require indexing datasets, use server-side
        // deferred to ensure that job is run. Also use deferred that
        // resolves to outputs from tool.
        var run_deferred = $.Deferred();

        var ss_deferred = new util.ServerStateDeferred({
            ajax_settings: {
                url: this.urlRoot,
                data: JSON.stringify(payload),
                dataType: "json",
                contentType: "application/json",
                type: "POST",
            },
            interval: 2000,
            success_fn: function (response) {
                return response !== "pending";
            },
        });

        // Run job and resolve run_deferred to tool outputs.
        $.when(ss_deferred.go()).then((result) => {
            run_deferred.resolve(new DatasetCollection(result));
        });
        return run_deferred;
    },
});
_.extend(Tool.prototype, VisibilityMixin);

/**
 * View for working with a tool: setting parameters and inputs and executing the tool.
 */
var ToolFormView = Backbone.View.extend({
    className: "toolForm",

    render: function () {
        this.$el.children().remove();
        this.$el.append(templates.tool_form(this.model.toJSON()));
    },
});

// TODO: move into relevant views
var templates = {
    // the tool form for entering tool parameters, viewing help and executing the tool
    // loaded when a tool link is clicked in the tool panel
    tool_form: _.template(
        [
            '<div class="toolFormTitle"><%- tool.name %> (version <%- tool.version %>)</div>',
            '<div class="toolFormBody">',
            "<% _.each( tool.inputs, function( input ){ %>",
            '<div class="form-row">',
            '<label for="<%- input.name %>"><%- input.label %>:</label>',
            '<div class="form-row-input">',
            "<%= input.html %>",
            "</div>",
            '<div class="toolParamHelp" style="clear: both;">',
            "<%- input.help %>",
            "</div>",
            '<div style="clear: both;"></div>',
            "</div>",
            "<% }); %>",
            "</div>",
            '<div class="form-row form-actions">',
            '<input type="submit" class="btn btn-primary" name="runtool_btn" value="Execute" />',
            "</div>",
            '<div class="toolHelp">',
            '<div class="toolHelpBody"><% tool.help %></div>',
            "</div>",
            // TODO: we need scoping here because 'help' is the dom for the help menu in the masthead
            // which implies a leaky variable that I can't find
        ].join(""),
        { variable: "tool" }
    ),
};

// Exports
export default {
    ToolParameter: ToolParameter,
    IntegerToolParameter: IntegerToolParameter,
    SelectToolParameter: SelectToolParameter,
    Tool: Tool,
    ToolFormView: ToolFormView,
};
