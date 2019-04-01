/**
 * Model, view, and controller objects for Galaxy tools and tool panel.
 */
/* global ga */
import _ from "underscore";
import $ from "jquery";
import d3 from "d3";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import util from "viz/trackster/util";
import { DatasetCollection } from "mvc/dataset/data";

/**
 * Mixin for tracking model visibility.
 */
var VisibilityMixin = {
    hidden: false,

    show: function() {
        this.set("hidden", false);
    },

    hide: function() {
        this.set("hidden", true);
    },

    toggle: function() {
        this.set("hidden", !this.get("hidden"));
    },

    is_visible: function() {
        return !this.attributes.hidden;
    }
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
        num_samples: 5
    },

    initialize: function(options) {
        this.attributes.html = unescape(this.attributes.html);
    },

    copy: function() {
        return new ToolParameter(this.toJSON());
    },

    set_value: function(value) {
        this.set("value", value || "");
    }
});

var ToolParameterCollection = Backbone.Collection.extend({
    model: ToolParameter
});

/**
 * A data tool parameter.
 */
var DataToolParameter = ToolParameter.extend({});

/**
 * An integer tool parameter.
 */
var IntegerToolParameter = ToolParameter.extend({
    set_value: function(value) {
        this.set("value", parseInt(value, 10));
    },

    /**
     * Returns samples from a tool input.
     */
    get_samples: function() {
        return d3.scale
            .linear()
            .domain([this.get("min"), this.get("max")])
            .ticks(this.get("num_samples"));
    }
});

var FloatToolParameter = IntegerToolParameter.extend({
    set_value: function(value) {
        this.set("value", parseFloat(value));
    }
});

/**
 * A select tool parameter.
 */
var SelectToolParameter = ToolParameter.extend({
    /**
     * Returns tool options.
     */
    get_samples: function() {
        return _.map(this.get("options"), option => option[0]);
    }
});

// Set up dictionary of parameter types.
ToolParameter.subModelTypes = {
    integer: IntegerToolParameter,
    float: FloatToolParameter,
    data: DataToolParameter,
    select: SelectToolParameter
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
        outputs: []
    },

    urlRoot: `${getAppRoot()}api/tools`,

    initialize: function(options) {
        // Set parameters.
        this.set(
            "inputs",
            new ToolParameterCollection(
                _.map(options.inputs, p => {
                    var p_class = ToolParameter.subModelTypes[p.type] || ToolParameter;
                    return new p_class(p);
                })
            )
        );
    },

    /**
     *
     */
    toJSON: function() {
        var rval = Backbone.Model.prototype.toJSON.call(this);

        // Convert inputs to JSON manually.
        rval.inputs = this.get("inputs").map(i => i.toJSON());
        return rval;
    },

    /**
     * Removes inputs of a particular type; this is useful because not all inputs can be handled by
     * client and server yet.
     */
    remove_inputs: function(types) {
        var tool = this;

        var incompatible_inputs = tool.get("inputs").filter(input => types.indexOf(input.get("type")) !== -1);

        tool.get("inputs").remove(incompatible_inputs);
    },

    /**
     * Returns object copy, optionally including only inputs that can be sampled.
     */
    copy: function(only_samplable_inputs) {
        var copy = new Tool(this.toJSON());

        // Return only samplable inputs if flag is set.
        if (only_samplable_inputs) {
            var valid_inputs = new Backbone.Collection();
            copy.get("inputs").each(input => {
                if (input.get_samples()) {
                    valid_inputs.push(input);
                }
            });
            copy.set("inputs", valid_inputs);
        }

        return copy;
    },

    apply_search_results: function(results) {
        _.indexOf(results, this.attributes.id) !== -1 ? this.show() : this.hide();
        return this.is_visible();
    },

    /**
     * Set a tool input's value.
     */
    set_input_value: function(name, value) {
        this.get("inputs")
            .find(input => input.get("name") === name)
            .set("value", value);
    },

    /**
     * Set many input values at once.
     */
    set_input_values: function(inputs_dict) {
        var self = this;
        _.each(_.keys(inputs_dict), input_name => {
            self.set_input_value(input_name, inputs_dict[input_name]);
        });
    },

    /**
     * Run tool; returns a Deferred that resolves to the tool's output(s).
     */
    run: function() {
        return this._run();
    },

    /**
     * Rerun tool using regions and a target dataset.
     */
    rerun: function(target_dataset, regions) {
        return this._run({
            action: "rerun",
            target_dataset_id: target_dataset.id,
            regions: regions
        });
    },

    /**
     * Returns input dict for tool's inputs.
     */
    get_inputs_dict: function() {
        var input_dict = {};
        this.get("inputs").each(input => {
            input_dict[input.get("name")] = input.get("value");
        });
        return input_dict;
    },

    /**
     * Run tool; returns a Deferred that resolves to the tool's output(s).
     * NOTE: this method is a helper method and should not be called directly.
     */
    _run: function(additional_params) {
        // Create payload.
        var payload = _.extend(
            {
                tool_id: this.id,
                inputs: this.get_inputs_dict()
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
                type: "POST"
            },
            interval: 2000,
            success_fn: function(response) {
                return response !== "pending";
            }
        });

        // Run job and resolve run_deferred to tool outputs.
        $.when(ss_deferred.go()).then(result => {
            run_deferred.resolve(new DatasetCollection(result));
        });
        return run_deferred;
    }
});
_.extend(Tool.prototype, VisibilityMixin);

/**
 * Wrap collection of tools for fast access/manipulation.
 */
var ToolCollection = Backbone.Collection.extend({
    model: Tool
});

/**
 * Label or section header in tool panel.
 */
var ToolSectionLabel = Backbone.Model.extend(VisibilityMixin);

/**
 * Section of tool panel with elements (labels and tools).
 */
var ToolSection = Backbone.Model.extend({
    defaults: {
        elems: [],
        open: false
    },

    clear_search_results: function() {
        _.each(this.attributes.elems, elt => {
            elt.show();
        });

        this.show();
        this.set("open", false);
    },

    apply_search_results: function(results) {
        var all_hidden = true;
        var cur_label;
        _.each(this.attributes.elems, elt => {
            if (elt instanceof ToolSectionLabel) {
                cur_label = elt;
                cur_label.hide();
            } else if (elt instanceof Tool) {
                if (elt.apply_search_results(results)) {
                    all_hidden = false;
                    if (cur_label) {
                        cur_label.show();
                    }
                }
            }
        });

        if (all_hidden) {
            this.hide();
        } else {
            this.show();
            this.set("open", true);
        }
    }
});
_.extend(ToolSection.prototype, VisibilityMixin);

/**
 * Tool search that updates results when query is changed. Result value of null
 * indicates that query was not run; if not null, results are from search using
 * query.
 */
var ToolSearch = Backbone.Model.extend({
    SEARCH_RESERVED_TERMS_FAVORITES: ["#favs", "#favorites", "#favourites"],

    defaults: {
        search_hint_string: "search tools",
        min_chars_for_search: 3,
        clear_btn_url: "",
        visible: true,
        query: "",
        results: null,
        // ESC (27) will clear the input field and tool search filters
        clear_key: 27
    },

    urlRoot: `${getAppRoot()}api/tools`,

    initialize: function() {
        this.on("change:query", this.do_search);
    },

    /**
     * Do the search and update the results.
     */
    do_search: function() {
        let Galaxy = getGalaxyInstance();
        var query = this.attributes.query;

        // If query is too short, do not search.
        if (query.length < this.attributes.min_chars_for_search) {
            this.set("results", null);
            return;
        }

        // Do search via AJAX.
        var q = query;
        // Stop previous ajax-request
        if (this.timer) {
            clearTimeout(this.timer);
        }
        // Catch reserved words
        if (this.SEARCH_RESERVED_TERMS_FAVORITES.indexOf(q) >= 0) {
            this.set("results", Galaxy.user.getFavorites().tools);
        } else {
            // Start a new ajax-request in X ms
            $("#search-clear-btn").hide();
            $("#search-spinner").show();
            var self = this;
            this.timer = setTimeout(() => {
                // log the search to analytics if present
                if (typeof ga !== "undefined") {
                    ga("send", "pageview", `${getAppRoot()}?q=${q}`);
                }
                $.get(
                    self.urlRoot,
                    { q: q },
                    data => {
                        self.set("results", data);
                        $("#search-spinner").hide();
                        $("#search-clear-btn").show();
                    },
                    "json"
                );
            }, 400);
        }
    },

    clear_search: function() {
        this.set("query", "");
        this.set("results", null);
    }
});
_.extend(ToolSearch.prototype, VisibilityMixin);

/**
 * Tool Panel.
 */
var ToolPanel = Backbone.Model.extend({
    initialize: function(options) {
        this.attributes.tool_search = options.tool_search;
        this.attributes.tool_search.on("change:results", this.apply_search_results, this);
        this.attributes.tools = options.tools;
        this.attributes.layout = new Backbone.Collection(this.parse(options.layout));
    },

    /**
     * Parse tool panel dictionary and return collection of tool panel elements.
     */
    parse: function(response) {
        // Recursive function to parse tool panel elements.
        var self = this;

        var // Helper to recursively parse tool panel.
            parse_elt = elt_dict => {
                var type = elt_dict.model_class;
                // There are many types of tools; for now, anything that ends in 'Tool'
                // is treated as a generic tool.
                if (type.indexOf("Tool") === type.length - 4) {
                    return self.attributes.tools.get(elt_dict.id);
                } else if (type === "ToolSection") {
                    // Parse elements.
                    var elems = _.map(elt_dict.elems, parse_elt);
                    elt_dict.elems = elems;
                    return new ToolSection(elt_dict);
                } else if (type === "ToolSectionLabel") {
                    return new ToolSectionLabel(elt_dict);
                }
            };

        return _.map(response, parse_elt);
    },

    clear_search_results: function() {
        this.get("layout").each(panel_elt => {
            if (panel_elt instanceof ToolSection) {
                panel_elt.clear_search_results();
            } else {
                // Label or tool, so just show.
                panel_elt.show();
            }
        });
    },

    apply_search_results: function() {
        var results = this.get("tool_search").get("results");
        if (results === null) {
            this.clear_search_results();
            return;
        }

        var cur_label = null;
        this.get("layout").each(panel_elt => {
            if (panel_elt instanceof ToolSectionLabel) {
                cur_label = panel_elt;
                cur_label.hide();
            } else if (panel_elt instanceof Tool) {
                if (panel_elt.apply_search_results(results)) {
                    if (cur_label) {
                        cur_label.show();
                    }
                }
            } else {
                // Starting new section, so clear current label.
                cur_label = null;
                panel_elt.apply_search_results(results);
            }
        });
    }
});

/**
 * View classes for Galaxy tools and tool panel.
 *
 * Views use the templates defined below for rendering. Views update as needed
 * based on (a) model/collection events and (b) user interactions; in this sense,
 * they are controllers are well and the HTML is the real view in the MVC architecture.
 */

/**
 * Base view that handles visibility based on model's hidden attribute.
 */
var BaseView = Backbone.View.extend({
    initialize: function() {
        this.model.on("change:hidden", this.update_visible, this);
        this.update_visible();
    },
    update_visible: function() {
        this.model.attributes.hidden ? this.$el.hide() : this.$el.show();
    }
});

/**
 * Link to a tool.
 */
var ToolLinkView = BaseView.extend({
    tagName: "div",

    render: function() {
        // create element
        var $link = $("<div/>");
        $link.append(templates.tool_link(this.model.toJSON()));

        var formStyle = this.model.get("form_style", null);
        // open upload dialog for upload tool
        if (this.model.id === "upload1") {
            $link.find("a").on("click", e => {
                e.preventDefault();
                let Galaxy = getGalaxyInstance();
                Galaxy.upload.show();
            });
        } else if (formStyle === "regular") {
            // regular tools
            var self = this;
            $link.find("a").on("click", e => {
                e.preventDefault();
                let Galaxy = getGalaxyInstance();
                Galaxy.router.push("/", {
                    tool_id: self.model.id,
                    version: self.model.get("version")
                });
            });
        }

        // add element
        this.$el.append($link);
        return this;
    }
});

/**
 * Panel label/section header.
 */
var ToolSectionLabelView = BaseView.extend({
    tagName: "div",
    className: "toolPanelLabel",

    render: function() {
        this.$el.append($("<span/>").text(this.model.attributes.text));
        return this;
    }
});

/**
 * Panel section.
 */
var ToolSectionView = BaseView.extend({
    tagName: "div",
    className: "toolSectionWrapper",

    initialize: function() {
        BaseView.prototype.initialize.call(this);
        this.model.on("change:open", this.update_open, this);
    },

    render: function() {
        // Build using template.
        this.$el.append(templates.panel_section(this.model.toJSON()));

        // Add tools to section.
        var section_body = this.$el.find(".toolSectionBody");
        _.each(this.model.attributes.elems, elt => {
            if (elt instanceof Tool) {
                var tool_view = new ToolLinkView({
                    model: elt,
                    className: "toolTitle"
                });
                tool_view.render();
                section_body.append(tool_view.$el);
            } else if (elt instanceof ToolSectionLabel) {
                var label_view = new ToolSectionLabelView({
                    model: elt
                });
                label_view.render();
                section_body.append(label_view.$el);
            } else {
                // TODO: handle nested section bodies?
            }
        });
        return this;
    },

    events: {
        "click .toolSectionTitle > a": "toggle"
    },

    /**
     * Toggle visibility of tool section.
     */
    toggle: function() {
        this.model.set("open", !this.model.attributes.open);
    },

    /**
     * Update whether section is open or close.
     */
    update_open: function() {
        this.model.attributes.open
            ? this.$el.children(".toolSectionBody").slideDown("fast")
            : this.$el.children(".toolSectionBody").slideUp("fast");
    }
});

var ToolSearchView = Backbone.View.extend({
    tagName: "div",
    id: "tool-search",
    className: "bar",

    events: {
        click: "focus_and_select",
        "keyup :input": "query_changed",
        "change :input": "query_changed",
        "click #search-clear-btn": "clear"
    },

    render: function() {
        this.$el.append(templates.tool_search(this.model.toJSON()));
        if (!this.model.is_visible()) {
            this.$el.hide();
        }

        this.$el.find("[title]").tooltip();
        return this;
    },

    focus_and_select: function() {
        this.$el
            .find(":input")
            .focus()
            .select();
    },

    clear: function() {
        this.model.clear_search();
        this.$el.find(":input").val("");
        this.focus_and_select();
        return false;
    },

    query_changed: function(evData) {
        // check for the 'clear key' (ESC) first
        if (this.model.attributes.clear_key && this.model.attributes.clear_key === evData.which) {
            this.clear();
            return false;
        }
        this.model.set("query", this.$el.find(":input").val());
    }
});

/**
 * Tool panel view. Events triggered include:
 * tool_link_click(click event, tool_model)
 */
var ToolPanelView = Backbone.View.extend({
    tagName: "div",
    className: "toolMenu",

    /**
     * Set up view.
     */
    initialize: function() {
        this.model.get("tool_search").on("change:results", this.handle_search_results, this);
    },

    render: function() {
        var self = this;

        // Render search.
        var search_view = new ToolSearchView({
            model: this.model.get("tool_search")
        });
        search_view.render();
        // FIXME: This is a little ugly because it navigates through the parent
        //        element, but good enough until this is all `.vue`
        self.$el
            .closest(".unified-panel")
            .find(".unified-panel-controls")
            .append(search_view.$el);

        // Render panel.
        this.model.get("layout").each(panel_elt => {
            if (panel_elt instanceof ToolSection) {
                var section_title_view = new ToolSectionView({
                    model: panel_elt
                });
                section_title_view.render();
                self.$el.append(section_title_view.$el);
            } else if (panel_elt instanceof Tool) {
                var tool_view = new ToolLinkView({
                    model: panel_elt,
                    className: "toolTitleNoSection"
                });
                tool_view.render();
                self.$el.append(tool_view.$el);
            } else if (panel_elt instanceof ToolSectionLabel) {
                var label_view = new ToolSectionLabelView({
                    model: panel_elt
                });
                label_view.render();
                self.$el.append(label_view.$el);
            }
        });

        // Setup tool link click eventing.
        self.$el.find("a.tool-link").click(function(e) {
            // Tool id is always the first class.
            var tool_id = $(this)
                .attr("class")
                .split(/\s+/)[0];

            var tool = self.model.get("tools").get(tool_id);

            self.trigger("tool_link_click", e, tool);
        });

        return this;
    },

    handle_search_results: function() {
        var results = this.model.get("tool_search").get("results");
        if (results && results.length === 0) {
            $("#search-no-results").show();
        } else {
            $("#search-no-results").hide();
        }
    }
});

/**
 * View for working with a tool: setting parameters and inputs and executing the tool.
 */
var ToolFormView = Backbone.View.extend({
    className: "toolForm",

    render: function() {
        this.$el.children().remove();
        this.$el.append(templates.tool_form(this.model.toJSON()));
    }
});

// TODO: move into relevant views
var templates = {
    // the search bar at the top of the tool panel
    tool_search: _.template(
        `<input id="tool-search-query" class="search-query parent-width" name="query"
                placeholder="<%- search_hint_string %>" autocomplete="off" type="text" />
         <a id="search-clear-btn" title="clear search (esc)"> </a>
         <span id="search-spinner" class="search-spinner fa fa-spinner fa-spin"></span>
    `
    ),

    // the category level container in the tool panel (e.g. 'Get Data', 'Text Manipulation')
    panel_section: _.template(
        [
            '<div class="toolSectionTitle" id="title_<%- id %>">',
            '<a href="javascript:void(0)"><span><%- name %></span></a>',
            "</div>",
            '<div id="<%- id %>" class="toolSectionBody" style="display: none;">',
            '<div class="toolSectionBg"></div>',
            "<div>"
        ].join("")
    ),

    // a single tool's link in the tool panel; will load the tool form in the center panel
    tool_link: _.template(
        [
            '<a class="<%- id %> tool-link" href="<%= link %>" target="<%- target %>" minsizehint="<%- min_width %>">',
            '<span class="labels">',
            "<% _.each( labels, function( label ){ %>",
            '<span class="badge badge-primary badge-<%- label %>">',
            "<%- label %>",
            "</span>",
            "<% }); %>",
            "</span>",
            '<span class="tool-old-link">',
            "<%- name %>",
            "</span>",
            " <%- description %>",
            "</a>"
        ].join("")
    ),

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
            "</div>"
            // TODO: we need scoping here because 'help' is the dom for the help menu in the masthead
            // which implies a leaky variable that I can't find
        ].join(""),
        { variable: "tool" }
    )
};

// Exports
export default {
    ToolParameter: ToolParameter,
    IntegerToolParameter: IntegerToolParameter,
    SelectToolParameter: SelectToolParameter,
    Tool: Tool,
    ToolCollection: ToolCollection,
    ToolSearch: ToolSearch,
    ToolPanel: ToolPanel,
    ToolPanelView: ToolPanelView,
    ToolFormView: ToolFormView
};
