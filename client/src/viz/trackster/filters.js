import $ from "jquery";
import _l from "utils/localization";
import _ from "underscore";
import { getGalaxyInstance } from "app";

/**
 * Filters that enable users to show/hide data points dynamically.
 */
var Filter = function (obj_dict) {
    this.manager = null;
    this.name = obj_dict.name;
    // Index into payload to filter.
    this.index = obj_dict.index;
    this.tool_id = obj_dict.tool_id;
    // Name to use for filter when building expression for tool.
    this.tool_exp_name = obj_dict.tool_exp_name;
};

_.extend(Filter.prototype, {
    /**
     * Convert filter to dictionary.
     */
    to_dict: function () {
        return {
            name: this.name,
            index: this.index,
            tool_id: this.tool_id,
            tool_exp_name: this.tool_exp_name,
        };
    },
});

/**
 * Creates an action icon.
 */
var create_action_icon = (title, css_class, on_click_fn) =>
    $("<a/>")
        .attr("href", "javascript:void(0);")
        .attr("title", title)
        .addClass("icon-button")
        .addClass(css_class)
        .tooltip()
        .click(on_click_fn);

/**
 * Number filters have a min, max as well as a low, high; low and high are used
 */
var NumberFilter = function (obj_dict) {
    //
    // Attribute init.
    //
    Filter.call(this, obj_dict);
    // Filter low/high. These values are used to filter elements.
    this.low = "low" in obj_dict ? obj_dict.low : -Number.MAX_VALUE;
    this.high = "high" in obj_dict ? obj_dict.high : Number.MAX_VALUE;
    // Slide min/max. These values are used to set/update slider.
    this.min = "min" in obj_dict ? obj_dict.min : Number.MAX_VALUE;
    this.max = "max" in obj_dict ? obj_dict.max : -Number.MAX_VALUE;
    // UI elements associated with filter.
    this.container = null;
    this.slider = null;
    this.slider_label = null;

    //
    // Create HTML.
    //

    // Function that supports inline text editing of slider values.
    // Enable users to edit parameter's value via a text box.
    var edit_slider_values = (container, span, slider) => {
        container.click(function () {
            var cur_value = span.text();
            var max = parseFloat(slider.slider("option", "max"));

            var input_size = max <= 1 ? 4 : max <= 1000000 ? max.toString().length : 6;

            var multi_value = false;
            var slider_row = $(this).parents(".slider-row");

            // Row now has input.
            slider_row.addClass("input");

            // Increase input size if there are two values.
            if (slider.slider("option", "values")) {
                input_size = 2 * input_size + 1;
                multi_value = true;
            }
            span.text("");
            // Temporary input for changing value.
            $("<input type='text'/>")
                .attr("size", input_size)
                .attr("maxlength", input_size)
                .attr("value", cur_value)
                .appendTo(span)
                .focus()
                .select()
                .click((e) => {
                    // Don't want click to propogate up to values_span and restart everything.
                    e.stopPropagation();
                })
                .blur(function () {
                    $(this).remove();
                    span.text(cur_value);
                    slider_row.removeClass("input");
                })
                .keyup(function (e) {
                    if (e.keyCode === 27) {
                        // Escape key.
                        $(this).trigger("blur");
                    } else if (e.keyCode === 13) {
                        //
                        // Enter/return key initiates callback. If new value(s) are in slider range,
                        // change value (which calls slider's change() function).
                        //
                        var slider_min = slider.slider("option", "min");

                        var slider_max = slider.slider("option", "max");

                        var invalid = (a_val) => isNaN(a_val) || a_val > slider_max || a_val < slider_min;

                        var new_value = $(this).val();
                        if (!multi_value) {
                            new_value = parseFloat(new_value);
                            if (invalid(new_value)) {
                                alert(`Parameter value must be in the range [${slider_min}-${slider_max}]`);
                                return $(this);
                            }
                        } else {
                            // Multi value.
                            new_value = new_value.split("-");
                            new_value = [parseFloat(new_value[0]), parseFloat(new_value[1])];
                            if (invalid(new_value[0]) || invalid(new_value[1])) {
                                alert(`Parameter value must be in the range [${slider_min}-${slider_max}]`);
                                return $(this);
                            }
                        }

                        // Updating the slider also updates slider values and removes input.
                        slider.slider(multi_value ? "values" : "value", new_value);
                        slider_row.removeClass("input");
                    }
                });
        });
    };

    var filter = this;

    filter.parent_div = $("<div/>").addClass("filter-row slider-row");

    // Set up filter label (name, values).
    var filter_label = $("<div/>").addClass("elt-label").appendTo(filter.parent_div);

    $("<span/>").addClass("slider-name").text(`${filter.name}  `).appendTo(filter_label);

    var values_span = $("<span/>").text(`${this.low}-${this.high}`);

    var values_span_container = $("<span/>")
        .addClass("slider-value")
        .appendTo(filter_label)
        .append("[")
        .append(values_span)
        .append("]");

    filter.values_span = values_span;

    // Set up slider for filter.
    var slider_div = $("<div/>").addClass("slider").appendTo(filter.parent_div);
    filter.control_element = $("<div/>").attr("id", `${filter.name}-filter-control`).appendTo(slider_div);
    filter.control_element.slider({
        range: true,
        min: this.min,
        max: this.max,
        step: this.get_slider_step(this.min, this.max),
        values: [this.low, this.high],
        slide: function (event, ui) {
            filter.slide(event, ui);
        },
        change: function (event, ui) {
            filter.control_element.slider("option", "slide").call(filter.control_element, event, ui);
        },
    });
    filter.slider = filter.control_element;
    filter.slider_label = values_span;

    // Enable users to edit slider values via text box.
    edit_slider_values(values_span_container, values_span, filter.control_element);

    // Set up filter display controls.
    var display_controls_div = $("<div/>").addClass("display-controls").appendTo(filter.parent_div);
    this.transparency_icon = create_action_icon("Use filter for data transparency", "layer-transparent", () => {
        if (filter.manager.alpha_filter !== filter) {
            // Setting this filter as the alpha filter.
            filter.manager.alpha_filter = filter;
            // Update UI for new filter.
            filter.manager.parent_div.find(".layer-transparent").removeClass("active").hide();
            filter.transparency_icon.addClass("active").show();
        } else {
            // Clearing filter as alpha filter.
            filter.manager.alpha_filter = null;
            filter.transparency_icon.removeClass("active");
        }
        filter.manager.track.request_draw({
            force: true,
            clear_after: true,
        });
    })
        .appendTo(display_controls_div)
        .hide();
    this.height_icon = create_action_icon("Use filter for data height", "arrow-resize-090", () => {
        if (filter.manager.height_filter !== filter) {
            // Setting this filter as the height filter.
            filter.manager.height_filter = filter;
            // Update UI for new filter.
            filter.manager.parent_div.find(".arrow-resize-090").removeClass("active").hide();
            filter.height_icon.addClass("active").show();
        } else {
            // Clearing filter as alpha filter.
            filter.manager.height_filter = null;
            filter.height_icon.removeClass("active");
        }
        filter.manager.track.request_draw({
            force: true,
            clear_after: true,
        });
    })
        .appendTo(display_controls_div)
        .hide();
    filter.parent_div.hover(
        () => {
            filter.transparency_icon.show();
            filter.height_icon.show();
        },
        () => {
            if (filter.manager.alpha_filter !== filter) {
                filter.transparency_icon.hide();
            }
            if (filter.manager.height_filter !== filter) {
                filter.height_icon.hide();
            }
        }
    );

    // Add to clear floating layout.
    $("<div style='clear: both;'/>").appendTo(filter.parent_div);
};

_.extend(NumberFilter.prototype, {
    /**
     * Convert filter to dictionary.
     */
    to_dict: function () {
        var obj_dict = Filter.prototype.to_dict.call(this);
        return _.extend(obj_dict, {
            type: "number",
            min: this.min,
            max: this.max,
            low: this.low,
            high: this.high,
        });
    },
    /**
     * Return a copy of filter.
     */
    copy: function () {
        return new NumberFilter({
            name: this.name,
            index: this.index,
            tool_id: this.tool_id,
            tool_exp_name: this.tool_exp_name,
        });
    },
    /**
     * Get step for slider.
     */
    // FIXME: make this a "static" function.
    get_slider_step: function (min, max) {
        var range = max - min;
        return range <= 2 ? 0.01 : 1;
    },
    /**
     * Handle slide events.
     */
    slide: function (event, ui) {
        var values = ui.values;

        // Set new values in UI.
        this.values_span.text(`${values[0]}-${values[1]}`);

        // Set new values in filter.
        this.low = values[0];
        this.high = values[1];

        // Set timeout to update if filter low, high are stable.
        var self = this;
        setTimeout(() => {
            if (values[0] === self.low && values[1] === self.high) {
                self.manager.track.request_draw({
                    force: true,
                    clear_after: true,
                });
            }
        }, 25);
    },
    /**
     * Returns true if filter can be applied to element.
     */
    applies_to: function (element) {
        return element.length > this.index;
    },
    /**
     * Helper function: returns true if value in in filter's [low, high] range.
     */
    _keep_val: function (val) {
        return isNaN(val) || (val >= this.low && val <= this.high);
    },
    /**
     * Returns true if (a) element's value(s) is in [low, high] (range is inclusive)
     * or (b) if value is non-numeric and hence unfilterable.
     */
    keep: function (element) {
        if (!this.applies_to(element)) {
            // No element to filter on.
            return true;
        }

        // Do filtering.
        var to_filter = element[this.index];
        if (to_filter instanceof Array) {
            var returnVal = true;
            for (var i = 0; i < to_filter.length; i++) {
                if (!this._keep_val(to_filter[i])) {
                    // Exclude element.
                    returnVal = false;
                    break;
                }
            }
            return returnVal;
        } else {
            return this._keep_val(element[this.index]);
        }
    },
    /**
     * Update filter's min and max values based on element's values.
     */
    update_attrs: function (element) {
        var updated = false;
        if (!this.applies_to(element)) {
            return updated;
        }

        //
        // Update filter's min, max based on element values.
        //

        // Make value(s) into an Array.
        var values = element[this.index];
        if (!(values instanceof Array)) {
            values = [values];
        }

        // Loop through values and update min, max.
        for (var i = 0; i < values.length; i++) {
            var value = values[i];
            if (value < this.min) {
                this.min = Math.floor(value);
                updated = true;
            }
            if (value > this.max) {
                this.max = Math.ceil(value);
                updated = true;
            }
        }
        return updated;
    },
    /**
     * Update filter's slider.
     */
    update_ui_elt: function () {
        // Only show filter if min < max because filter is not useful otherwise. This
        // covers all corner cases, such as when min, max have not been defined and
        // when min == max.
        if (this.min < this.max) {
            this.parent_div.show();
        } else {
            this.parent_div.hide();
        }

        var slider_min = this.slider.slider("option", "min");
        var slider_max = this.slider.slider("option", "max");
        if (this.min < slider_min || this.max > slider_max) {
            // Update slider min, max, step.
            this.slider.slider("option", "min", this.min);
            this.slider.slider("option", "max", this.max);
            this.slider.slider("option", "step", this.get_slider_step(this.min, this.max));
            // Refresh slider:
            // TODO: do we want to keep current values or reset to min/max?
            // Currently we reset values:
            this.slider.slider("option", "values", [this.min, this.max]);
            // To use the current values.
            //var values = this.slider.slider( "option", "values" );
            //this.slider.slider( "option", "values", values );
        }
    },
});

/**
 * Manages a set of filters.
 */
var FiltersManager = function (track, obj_dict) {
    this.track = track;
    this.alpha_filter = null;
    this.height_filter = null;
    this.filters = [];

    //
    // Create HTML.
    //

    //
    // Create parent div.
    //
    this.parent_div = $("<div/>").addClass("filters").hide();
    // Disable dragging, double clicking, keys on div so that actions on slider do not impact viz.
    this.parent_div
        .bind("drag", (e) => {
            e.stopPropagation();
        })
        .click((e) => {
            e.stopPropagation();
        })
        .bind("dblclick", (e) => {
            e.stopPropagation();
        })
        .bind("keydown", (e) => {
            e.stopPropagation();
        });

    //
    // Restore state from dict.
    //
    if (obj_dict && "filters" in obj_dict) {
        // Second condition needed for backward compatibility.
        var alpha_filter_name = "alpha_filter" in obj_dict ? obj_dict.alpha_filter : null;

        var height_filter_name = "height_filter" in obj_dict ? obj_dict.height_filter : null;

        var filters_dict = obj_dict.filters;
        var filter;
        for (var i = 0; i < filters_dict.length; i++) {
            if (filters_dict[i].type === "number") {
                filter = new NumberFilter(filters_dict[i]);
                this.add_filter(filter);
                if (filter.name === alpha_filter_name) {
                    this.alpha_filter = filter;
                    filter.transparency_icon.addClass("active").show();
                }
                if (filter.name === height_filter_name) {
                    this.height_filter = filter;
                    filter.height_icon.addClass("active").show();
                }
            } else {
                console.log("ERROR: unsupported filter: ", filters_dict[i]);
            }
        }

        if ("visible" in obj_dict && obj_dict.visible) {
            this.parent_div.show();
        }
    }

    // Add button to filter complete dataset.
    if (this.filters.length !== 0) {
        var run_buttons_row = $("<div/>").addClass("param-row").appendTo(this.parent_div);
        var run_on_dataset_button = $("<input type='submit'/>")
            .attr("value", "Run on complete dataset")
            .appendTo(run_buttons_row);
        var filter_manager = this;
        run_on_dataset_button.click(() => {
            filter_manager.run_on_dataset();
        });
    }
};

_.extend(FiltersManager.prototype, {
    // HTML manipulation and inspection.
    show: function () {
        this.parent_div.show();
    },
    hide: function () {
        this.parent_div.hide();
    },
    toggle: function () {
        this.parent_div.toggle();
    },
    visible: function () {
        return this.parent_div.is(":visible");
    },
    /**
     * Returns dictionary for manager.
     */
    to_dict: function () {
        var obj_dict = {};
        var filter_dicts = [];
        var filter;

        // Include individual filter states.
        for (var i = 0; i < this.filters.length; i++) {
            filter = this.filters[i];
            filter_dicts.push(filter.to_dict());
        }
        obj_dict.filters = filter_dicts;

        // Include transparency, height filters.
        obj_dict.alpha_filter = this.alpha_filter ? this.alpha_filter.name : null;
        obj_dict.height_filter = this.height_filter ? this.height_filter.name : null;

        // Include visibility.
        obj_dict.visible = this.parent_div.is(":visible");

        return obj_dict;
    },
    /**
     * Return a copy of the manager.
     */
    copy: function (new_track) {
        var copy = new FiltersManager(new_track);
        for (var i = 0; i < this.filters.length; i++) {
            copy.add_filter(this.filters[i].copy());
        }
        return copy;
    },
    /**
     * Add a filter to the manager.
     */
    add_filter: function (filter) {
        filter.manager = this;
        this.parent_div.append(filter.parent_div);
        this.filters.push(filter);
    },
    /**
     * Remove all filters from manager.
     */
    remove_all: function () {
        this.filters = [];
        this.parent_div.children().remove();
    },
    /**
     * Initialize filters.
     */

    init_filters: function () {
        for (var i = 0; i < this.filters.length; i++) {
            var filter = this.filters[i];
            filter.update_ui_elt();
        }
    },
    /**
     * Clear filters so that they do not impact track display.
     */
    clear_filters: function () {
        for (var i = 0; i < this.filters.length; i++) {
            var filter = this.filters[i];
            filter.slider.slider("option", "values", [filter.min, filter.max]);
        }
        this.alpha_filter = null;
        this.height_filter = null;

        // Hide icons for setting filters.
        this.parent_div.find(".icon-button").hide();
    },
    run_on_dataset: function () {
        // Get or create dictionary item.
        var get_or_create_dict_item = (dict, key, new_item) => {
            // Add new item to dict if
            if (!(key in dict)) {
                dict[key] = new_item;
            }
            return dict[key];
        };

        //
        // Find and group active filters. Active filters are those being used to hide data.
        // Filters with the same tool id are grouped.
        //
        var active_filters = {};

        var filter;
        var tool_filter_conditions;
        for (var i = 0; i < this.filters.length; i++) {
            filter = this.filters[i];
            if (filter.tool_id) {
                // Add filtering conditions if filter low/high are set.
                if (filter.min !== filter.low) {
                    tool_filter_conditions = get_or_create_dict_item(active_filters, filter.tool_id, []);
                    tool_filter_conditions[tool_filter_conditions.length] = `${filter.tool_exp_name} >= ${filter.low}`;
                }
                if (filter.max !== filter.high) {
                    tool_filter_conditions = get_or_create_dict_item(active_filters, filter.tool_id, []);
                    tool_filter_conditions[tool_filter_conditions.length] = `${filter.tool_exp_name} <= ${filter.high}`;
                }
            }
        }

        //
        // Use tools to run filters.
        //

        // Create list of (tool_id, tool_filters) tuples.
        var active_filters_list = [];
        for (var tool_id in active_filters) {
            active_filters_list[active_filters_list.length] = [tool_id, active_filters[tool_id]];
        }

        // Invoke recursive function to run filters; this enables chaining of filters via
        // iteratively application.
        (function run_filter(input_dataset_id, filters) {
            var // Set up filtering info and params.
                filter_tuple = filters[0];

            var tool_id = filter_tuple[0];
            var tool_filters = filter_tuple[1];
            var tool_filter_str = `(${tool_filters.join(") and (")})`;

            var url_params = {
                cond: tool_filter_str,
                input: input_dataset_id,
                target_dataset_id: input_dataset_id,
                tool_id: tool_id,
            };

            // Remove current filter.
            filters = filters.slice(1);

            // DBTODO: This will never work, run_tool_url doesn't exist?
            // https://github.com/galaxyproject/galaxy/issues/7224
            // eslint-disable-next-line no-undef
            $.getJSON(run_tool_url, url_params, (response) => {
                const Galaxy = getGalaxyInstance();
                if (response.error) {
                    // General error.
                    Galaxy.modal.show({
                        title: _l("Filter Dataset"),
                        body: `Error running tool ${tool_id}`,
                        buttons: { Close: Galaxy.modal.hide() },
                    });
                } else if (filters.length === 0) {
                    // No more filters to run.
                    Galaxy.modal.show({
                        title: _l("Filtering Dataset"),
                        body: "Filter(s) are running on the complete dataset. Outputs are in dataset's history.",
                        buttons: { Close: Galaxy.modal.hide() },
                    });
                } else {
                    // More filters to run.
                    run_filter(response.dataset_id, filters);
                }
            });
        })(this.track.dataset_id, active_filters_list);
    },
});

export default {
    FiltersManager: FiltersManager,
    NumberFilter: NumberFilter,
};
