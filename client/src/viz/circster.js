import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import * as d3 from "d3";
import { event as currentEvent } from "d3";
import visualization from "viz/visualization";
import mod_utils from "utils/utils";
import config from "utils/config";
import mod_icon_btn from "mvc/ui/icon-button";
import "libs/farbtastic";

/**
 * Utility class for working with SVG.
 */

var SVGUtils = Backbone.Model.extend({
    /**
     * Returns true if element is visible.
     */
    is_visible: function (svg_elt, svg) {
        var eltBRect = svg_elt.getBoundingClientRect();
        var svgBRect = $("svg")[0].getBoundingClientRect();

        if (
            // To the left of screen?
            eltBRect.right < 0 ||
            // To the right of screen?
            eltBRect.left > svgBRect.right ||
            // Above screen?
            eltBRect.bottom < 0 ||
            // Below screen?
            eltBRect.top > svgBRect.bottom
        ) {
            return false;
        }
        return true;
    },
});

/**
 * Mixin for using ticks.
 */
var UsesTicks = {
    drawTicks: function (parent_elt, data, dataHandler, textTransform, horizontal) {
        // Set up group elements for chroms and for each tick.
        var ticks = parent_elt
            .append("g")
            .selectAll("g")
            .data(data)
            .enter()
            .append("g")
            .selectAll("g")
            .data(dataHandler)
            .enter()
            .append("g")
            .attr("class", "tick")
            .attr("transform", (d) => `rotate(${(d.angle * 180) / Math.PI - 90})translate(${d.radius},0)`);

        // Add line + text for ticks.
        var tick_coords = [];

        var text_coords = [];

        var text_anchor = (d) => (d.angle > Math.PI ? "end" : null);

        if (horizontal) {
            tick_coords = [0, 0, 0, -4];
            text_coords = [4, 0, "", ".35em"];
            text_anchor = null;
        } else {
            tick_coords = [1, 0, 4, 0];
            text_coords = [0, 4, ".35em", ""];
        }

        ticks
            .append("line")
            .attr("x1", tick_coords[0])
            .attr("y1", tick_coords[1])
            .attr("x2", tick_coords[2])
            .attr("y1", tick_coords[3])
            .style("stroke", "#000");

        return ticks
            .append("text")
            .attr("x", text_coords[0])
            .attr("y", text_coords[1])
            .attr("dx", text_coords[2])
            .attr("dy", text_coords[3])
            .attr("text-anchor", text_anchor)
            .attr("transform", textTransform)
            .text((d) => d.label);
    },

    /**
     * Format number for display at a tick.
     */
    formatNum: function (num, sigDigits) {
        // Use default of 2 sig. digits.
        if (sigDigits === undefined) {
            sigDigits = 2;
        }

        // Verify input number
        if (num === null) {
            return null;
        }

        // Calculate return value
        var rval = null;
        if (Math.abs(num) < 1) {
            rval = num.toPrecision(sigDigits);
        } else {
            // Use round to turn string from toPrecision() back into a number.
            var roundedNum = Math.round(num.toPrecision(sigDigits));

            // Use abbreviations.
            num = Math.abs(num);
            if (num < 1000) {
                rval = roundedNum;
            } else if (num < 1000000) {
                // Use K.
                rval = `${Math.round((roundedNum / 1000).toPrecision(3)).toFixed(0)}K`;
            } else if (num < 1000000000) {
                // Use M.
                rval = `${Math.round((roundedNum / 1000000).toPrecision(3)).toFixed(0)}M`;
            }
        }

        return rval;
    },
};

/**
 * A label track.
 */
var CircsterLabelTrack = Backbone.Model.extend({});

/**
 * Renders a full circster visualization.
 */
var CircsterView = Backbone.View.extend({
    className: "circster",

    initialize: function (options) {
        this.genome = options.genome;
        this.label_arc_height = 50;
        this.scale = 1;
        this.circular_views = null;
        this.chords_views = null;

        // When tracks added to/removed from model, update view.
        this.model.get("drawables").on("add", this.add_track, this);
        this.model.get("drawables").on("remove", this.remove_track, this);

        // When config settings change, update view.
        var vis_config = this.model.get("config");
        vis_config.get("arc_dataset_height").on("change:value", this.update_track_bounds, this);
        vis_config.get("track_gap").on("change:value", this.update_track_bounds, this);
    },

    // HACKs: using track_type for circular/chord distinction in the functions below for now.

    /**
     * Returns tracks to be rendered using circular view.
     */
    get_circular_tracks: function () {
        return this.model.get("drawables").filter((track) => track.get("track_type") !== "DiagonalHeatmapTrack");
    },

    /**
     * Returns tracks to be rendered using chords view.
     */
    get_chord_tracks: function () {
        return this.model.get("drawables").filter((track) => track.get("track_type") === "DiagonalHeatmapTrack");
    },

    /**
     * Returns a list of circular tracks' radius bounds.
     */
    get_tracks_bounds: function () {
        var circular_tracks = this.get_circular_tracks();

        var dataset_arc_height = this.model.get("config").get_value("arc_dataset_height");

        var track_gap = this.model.get("config").get_value("track_gap");

        var // Subtract 20 to make sure chrom labels are on screen.
            min_dimension = Math.min(this.$el.width(), this.$el.height()) - 20;

        var // Compute radius start based on model, will be centered
            // and fit entirely inside element by default.
            radius_start =
                min_dimension / 2 -
                circular_tracks.length * (dataset_arc_height + track_gap) +
                // Add track_gap back in because no gap is needed for last track.
                track_gap -
                this.label_arc_height;

        var // Compute range of track starting radii.
            tracks_start_radii = d3.range(radius_start, min_dimension / 2, dataset_arc_height + track_gap);

        // Map from track start to bounds.
        return _.map(tracks_start_radii, (radius) => [radius, radius + dataset_arc_height]);
    },

    /**
     * Renders circular tracks, chord tracks, and label tracks.
     */
    render: function () {
        var self = this;
        var width = self.$el.width();
        var height = self.$el.height();
        var circular_tracks = this.get_circular_tracks();
        var chords_tracks = this.get_chord_tracks();
        var total_gap = self.model.get("config").get_value("total_gap");
        var tracks_bounds = this.get_tracks_bounds();

        var // Set up SVG element.
            svg = d3
                .select(self.$el[0])
                .append("svg")
                .attr("width", width)
                .attr("height", height)
                .attr("pointer-events", "all")
                // Set up zooming, dragging.
                .append("svg:g")
                .call(
                    d3.behavior.zoom().on("zoom", () => {
                        // Do zoom, drag.
                        var scale = currentEvent.scale;
                        svg.attr("transform", `translate(${currentEvent.translate}) scale(${scale})`);

                        // Propagate scale changes to views.
                        if (self.scale !== scale) {
                            // Use timeout to wait for zooming/dragging to stop before rendering more detail.
                            if (self.zoom_drag_timeout) {
                                clearTimeout(self.zoom_drag_timeout);
                            }
                            self.zoom_drag_timeout = setTimeout(() => {
                                // Render more detail in tracks' visible elements.
                                // FIXME: do not do this right now; it is not fully implemented--e.g. data bounds
                                // are not updated when new data is fetched--and fetching more detailed quantitative
                                // data is not that useful.
                                /*
                        _.each(self.circular_views, function(view) {
                            view.update_scale(scale);
                        });
                        */
                            }, 400);
                        }
                    })
                )
                .attr("transform", `translate(${width / 2},${height / 2})`)
                .append("svg:g")
                .attr("class", "tracks");

        // -- Render circular tracks. --

        // Create a view for each track in the visualization and render.
        this.circular_views = circular_tracks.map((track, index) => {
            var view = new CircsterBigWigTrackView({
                el: svg.append("g")[0],
                track: track,
                radius_bounds: tracks_bounds[index],
                genome: self.genome,
                total_gap: total_gap,
            });

            view.render();

            return view;
        });

        // -- Render chords tracks. --

        this.chords_views = chords_tracks.map((track) => {
            var view = new CircsterChromInteractionsTrackView({
                el: svg.append("g")[0],
                track: track,
                radius_bounds: tracks_bounds[0],
                genome: self.genome,
                total_gap: total_gap,
            });

            view.render();

            return view;
        });

        // -- Render label track. --

        // Track bounds are:
        // (a) outer radius of last circular track;
        // (b)
        var outermost_radius = this.circular_views[this.circular_views.length - 1].radius_bounds[1];

        var track_bounds = [outermost_radius, outermost_radius + this.label_arc_height];

        this.label_track_view = new CircsterChromLabelTrackView({
            el: svg.append("g")[0],
            track: new CircsterLabelTrack(),
            radius_bounds: track_bounds,
            genome: self.genome,
            total_gap: total_gap,
        });

        this.label_track_view.render();
    },

    /**
     * Render a single track on the outside of the current visualization.
     */
    add_track: function (new_track) {
        var total_gap = this.model.get("config").get_value("total_gap");

        if (new_track.get("track_type") === "DiagonalHeatmapTrack") {
            // Added chords track.
            var innermost_radius_bounds = this.circular_views[0].radius_bounds;

            var new_view = new CircsterChromInteractionsTrackView({
                el: d3.select("g.tracks").append("g")[0],
                track: new_track,
                radius_bounds: innermost_radius_bounds,
                genome: this.genome,
                total_gap: total_gap,
            });

            new_view.render();
            this.chords_views.push(new_view);
        } else {
            // Added circular track.

            // Recompute and update circular track bounds.
            var new_track_bounds = this.get_tracks_bounds();
            _.each(this.circular_views, (track_view, i) => {
                track_view.update_radius_bounds(new_track_bounds[i]);
            });

            // Update chords tracks.
            _.each(this.chords_views, (track_view) => {
                track_view.update_radius_bounds(new_track_bounds[0]);
            });

            // Render new track.
            var track_index = this.circular_views.length;

            var track_view = new CircsterBigWigTrackView({
                el: d3.select("g.tracks").append("g")[0],
                track: new_track,
                radius_bounds: new_track_bounds[track_index],
                genome: this.genome,
                total_gap: total_gap,
            });

            track_view.render();
            this.circular_views.push(track_view);

            // Update label track.
            /*
            FIXME: should never have to update label track because vis always expands to fit area
            within label track.
            var track_bounds = new_track_bounds[ new_track_bounds.length-1 ];
            track_bounds[1] = track_bounds[0];
            this.label_track_view.update_radius_bounds(track_bounds);
            */
        }
    },

    /**
     * Remove a track from the view.
     */
    remove_track: function (track, tracks, options) {
        // -- Remove track from view. --
        var track_view = this.circular_views[options.index];
        this.circular_views.splice(options.index, 1);
        track_view.$el.remove();

        // Recompute and update track bounds.
        var new_track_bounds = this.get_tracks_bounds();
        _.each(this.circular_views, (track_view, i) => {
            track_view.update_radius_bounds(new_track_bounds[i]);
        });
    },

    update_track_bounds: function () {
        // Recompute and update track bounds.
        var new_track_bounds = this.get_tracks_bounds();
        _.each(this.circular_views, (track_view, i) => {
            track_view.update_radius_bounds(new_track_bounds[i]);
        });

        // Update chords tracks.
        _.each(this.chords_views, (track_view) => {
            track_view.update_radius_bounds(new_track_bounds[0]);
        });
    },
});

/**
 * Renders a track in a Circster visualization.
 */
var CircsterTrackView = Backbone.View.extend({
    tagName: "g",

    /* ----------------------- Public Methods ------------------------- */

    initialize: function (options) {
        this.bg_stroke = "#ddd";
        // Fill color when loading data.
        this.loading_bg_fill = "#ffc";
        // Fill color when data has been loaded.
        this.bg_fill = "#ddd";
        this.total_gap = options.total_gap;
        this.track = options.track;
        this.radius_bounds = options.radius_bounds;
        this.genome = options.genome;
        this.chroms_layout = this._chroms_layout();
        this.data_bounds = [];
        this.scale = 1;
        this.parent_elt = d3.select(this.$el[0]);
    },

    /**
     * Get fill color from config.
     */
    get_fill_color: function () {
        var color = this.track.get("config").get_value("block_color");
        if (!color) {
            color = this.track.get("config").get_value("color");
        }
        return color;
    },

    /**
     * Render track's data by adding SVG elements to parent.
     */
    render: function () {
        // -- Create track group element. --
        var track_parent_elt = this.parent_elt;

        // -- Render background arcs. --
        var genome_arcs = this.chroms_layout;

        var arc_gen = d3.svg.arc().innerRadius(this.radius_bounds[0]).outerRadius(this.radius_bounds[1]);

        var // Attach data to group element.
            chroms_elts = track_parent_elt.selectAll("g").data(genome_arcs).enter().append("svg:g");

        var // Draw chrom arcs/paths.
            chroms_paths = chroms_elts
                .append("path")
                .attr("d", arc_gen)
                .attr("class", "chrom-background")
                .style("stroke", this.bg_stroke)
                .style("fill", this.loading_bg_fill);

        // Append titles to paths.
        chroms_paths.append("title").text((d) => d.data.chrom);

        // -- Render track data and, when track data is rendered, apply preferences and update chrom_elts fill. --

        var self = this;

        var data_manager = self.track.get("data_manager");

        var // If track has a data manager, get deferred that resolves when data is ready.
            data_ready_deferred = data_manager ? data_manager.data_is_ready() : true;

        // When data is ready, render track.
        $.when(data_ready_deferred).then(() => {
            $.when(self._render_data(track_parent_elt)).then(() => {
                chroms_paths.style("fill", self.bg_fill);

                // Render labels after data is available so that data attributes are available.
                self.render_labels();
            });
        });
    },

    /**
     * Render track labels.
     */
    render_labels: function () {},

    /**
     * Update radius bounds.
     */
    update_radius_bounds: function (radius_bounds) {
        // Update bounds.
        this.radius_bounds = radius_bounds;

        // -- Update background arcs. --
        var new_d = d3.svg.arc().innerRadius(this.radius_bounds[0]).outerRadius(this.radius_bounds[1]);

        this.parent_elt.selectAll("g>path.chrom-background").transition().duration(1000).attr("d", new_d);

        this._transition_chrom_data();

        this._transition_labels();
    },

    /**
     * Update view scale. This fetches more data if scale is increased.
     */
    update_scale: function (new_scale) {
        // -- Update scale and return if new scale is less than old scale. --

        var old_scale = this.scale;
        this.scale = new_scale;
        if (new_scale <= old_scale) {
            return;
        }

        // -- Scale increased, so render visible data with more detail. --

        var self = this;

        var utils = new SVGUtils();

        // Select all chrom data and filter to operate on those that are visible.
        this.parent_elt
            .selectAll("path.chrom-data")
            .filter(function (d, i) {
                return utils.is_visible(this);
            })
            .each(function (d, i) {
                // -- Now operating on a single path element representing chromosome data. --

                var path_elt = d3.select(this);

                var chrom = path_elt.attr("chrom");
                var chrom_region = self.genome.get_chrom_region(chrom);
                var data_manager = self.track.get("data_manager");
                var data_deferred;

                // If can't get more detailed data, return.
                if (!data_manager.can_get_more_detailed_data(chrom_region)) {
                    return;
                }

                // -- Get more detailed data. --
                data_deferred = self.track
                    .get("data_manager")
                    .get_more_detailed_data(chrom_region, "Coverage", 0, new_scale);

                // When more data is available, use new data to redraw path.
                $.when(data_deferred).then((data) => {
                    // Remove current data path.
                    path_elt.remove();

                    // Update data bounds with new data.
                    self._update_data_bounds();

                    // Find chromosome arc to draw data on.
                    var chrom_arc = _.find(self.chroms_layout, (layout) => layout.data.chrom === chrom);

                    // Add new data path and apply preferences.
                    var color = self.get_fill_color();
                    self._render_chrom_data(self.parent_elt, chrom_arc, data)
                        .style("stroke", color)
                        .style("fill", color);
                });
            });

        return self;
    },

    /* ----------------------- Internal Methods ------------------------- */

    /**
     * Transitions chrom data to new values (e.g new radius or data bounds).
     */
    _transition_chrom_data: function () {
        var track = this.track;
        var chrom_arcs = this.chroms_layout;
        var chrom_data_paths = this.parent_elt.selectAll("g>path.chrom-data");
        var num_paths = chrom_data_paths[0].length;

        if (num_paths > 0) {
            var self = this;
            $.when(track.get("data_manager").get_genome_wide_data(this.genome)).then((genome_wide_data) => {
                // Map chrom data to path data, filtering out null values.
                var path_data = _.reject(
                    _.map(genome_wide_data, (chrom_data, i) => {
                        var rval = null;

                        var path_fn = self._get_path_function(chrom_arcs[i], chrom_data);

                        if (path_fn) {
                            rval = path_fn(chrom_data.data);
                        }
                        return rval;
                    }),
                    (p_data) => p_data === null
                );

                // Transition each path for data and color.
                var color = track.get("config").get_value("color");
                chrom_data_paths.each(function (path, index) {
                    d3.select(this)
                        .transition()
                        .duration(1000)
                        .style("stroke", color)
                        .style("fill", color)
                        .attr("d", path_data[index]);
                });
            });
        }
    },

    /**
     * Transition labels to new values (e.g new radius or data bounds).
     */
    _transition_labels: function () {},

    /**
     * Update data bounds. If there are new_bounds, use them; otherwise use
     * default data bounds.
     */
    _update_data_bounds: function (new_bounds) {
        this.data_bounds =
            new_bounds || this.get_data_bounds(this.track.get("data_manager").get_genome_wide_data(this.genome));
        this._transition_chrom_data();
    },

    /**
     * Render data as elements attached to svg.
     */
    _render_data: function (svg) {
        var self = this;
        var chrom_arcs = this.chroms_layout;
        var track = this.track;
        var rendered_deferred = $.Deferred();

        // When genome-wide data is available, render data.
        $.when(track.get("data_manager").get_genome_wide_data(this.genome)).then((genome_wide_data) => {
            // Set bounds.
            self.data_bounds = self.get_data_bounds(genome_wide_data);

            // Set min, max value in config so that they can be adjusted. Make this silent
            // because these attributes are watched for changes and the viz is updated
            // accordingly (set up in initialize). Because we are setting up, we don't want
            // the watch to trigger events here.
            track.get("config").set_value("min_value", self.data_bounds[0], {
                silent: true,
            });
            track.get("config").set_value("max_value", self.data_bounds[1], {
                silent: true,
            });

            // Merge chroms layout with data.
            var layout_and_data = _.zip(chrom_arcs, genome_wide_data);

            // Render each chromosome's data.
            _.each(layout_and_data, (chrom_info) => {
                var chrom_arc = chrom_info[0];
                var data = chrom_info[1];
                return self._render_chrom_data(svg, chrom_arc, data);
            });

            // Apply prefs to all track data.
            var color = self.get_fill_color();
            self.parent_elt.selectAll("path.chrom-data").style("stroke", color).style("fill", color);

            rendered_deferred.resolve(svg);
        });

        return rendered_deferred;
    },

    /**
     * Render a chromosome data and attach elements to svg.
     */
    _render_chrom_data: function (svg, chrom_arc, data) {},

    /**
     * Returns data for creating a path for the given data using chrom_arc and data bounds.
     */
    _get_path_function: function (chrom_arc, chrom_data) {},

    /**
     * Returns arc layouts for genome's chromosomes/contigs. Arcs are arranged in a circle
     * separated by gaps.
     */
    _chroms_layout: function () {
        // Setup chroms layout using pie.
        var chroms_info = this.genome.get_chroms_info();

        var pie_layout = d3.layout
            .pie()
            .value((d) => d.len)
            .sort(null);

        var init_arcs = pie_layout(chroms_info);
        var gap_per_chrom = (2 * Math.PI * this.total_gap) / chroms_info.length;

        var chrom_arcs = _.map(init_arcs, (arc, index) => {
            // For short chroms, endAngle === startAngle.
            var new_endAngle = arc.endAngle - gap_per_chrom;
            arc.endAngle = new_endAngle > arc.startAngle ? new_endAngle : arc.startAngle;
            return arc;
        });

        return chrom_arcs;
    },
});

/**
 * Render chromosome labels.
 */
var CircsterChromLabelTrackView = CircsterTrackView.extend({
    initialize: function (options) {
        CircsterTrackView.prototype.initialize.call(this, options);
        // Use a single arc for rendering data.
        this.innerRadius = this.radius_bounds[0];
        this.radius_bounds[0] = this.radius_bounds[1];
        this.bg_stroke = "#fff";
        this.bg_fill = "#fff";

        // Minimum arc distance for labels to be applied.
        this.min_arc_len = 0.05;
    },

    /**
     * Render labels.
     */
    _render_data: function (svg) {
        // -- Add chromosome label where it will fit; an alternative labeling mechanism
        // would be nice for small chromosomes. --
        var self = this;

        var chrom_arcs = svg.selectAll("g");

        chrom_arcs.selectAll("path").attr("id", (d) => `label-${d.data.chrom}`);

        chrom_arcs
            .append("svg:text")
            .filter((d) => d.endAngle - d.startAngle > self.min_arc_len)
            .attr("text-anchor", "middle")
            .append("svg:textPath")
            .attr("class", "chrom-label")
            .attr("xlink:href", (d) => `#label-${d.data.chrom}`)
            .attr("startOffset", "25%")
            .text((d) => d.data.chrom);

        // -- Add ticks to denote chromosome length. --

        /** Returns an array of tick angles and labels, given a chrom arc. */
        var chromArcTicks = (d) => {
            var k = (d.endAngle - d.startAngle) / d.value;

            var ticks = d3.range(0, d.value, 25000000).map((v, i) => ({
                radius: self.innerRadius,
                angle: v * k + d.startAngle,
                label: i === 0 ? 0 : i % 3 ? null : self.formatNum(v),
            }));

            // If there are fewer that 4 ticks, label last tick so that at least one non-zero tick is labeled.
            if (ticks.length < 4) {
                ticks[ticks.length - 1].label = self.formatNum(
                    Math.round((ticks[ticks.length - 1].angle - d.startAngle) / k)
                );
            }

            return ticks;
        };

        /** Rotate and move text as needed. */
        var textTransform = (d) => (d.angle > Math.PI ? "rotate(180)translate(-16)" : null);

        // Filter chroms for only those large enough for display.
        var visibleChroms = _.filter(this.chroms_layout, (c) => c.endAngle - c.startAngle > self.min_arc_len);

        this.drawTicks(this.parent_elt, visibleChroms, chromArcTicks, textTransform);
    },
});
_.extend(CircsterChromLabelTrackView.prototype, UsesTicks);

/**
 * View for quantitative track in Circster.
 */
var CircsterQuantitativeTrackView = CircsterTrackView.extend({
    initialize: function (options) {
        CircsterTrackView.prototype.initialize.call(this, options);

        // When config settings change, update view.
        var track_config = this.track.get("config");
        track_config.get("min_value").on("change:value", this._update_min_max, this);
        track_config.get("max_value").on("change:value", this._update_min_max, this);
        track_config.get("color").on("change:value", this._transition_chrom_data, this);
    },

    /**
     * Update track when min and/or max are changed.
     */
    _update_min_max: function () {
        var track_config = this.track.get("config");

        var new_bounds = [track_config.get_value("min_value"), track_config.get_value("max_value")];

        this._update_data_bounds(new_bounds);

        // FIXME: this works to update tick/text bounds, but there's probably a better way to do this
        // by updating the data itself.
        this.parent_elt.selectAll(".min_max").text((d, i) => new_bounds[i]);
    },

    /**
     * Returns quantile for an array of numbers.
     */
    _quantile: function (numbers, quantile) {
        numbers.sort(d3.ascending);
        return d3.quantile(numbers, quantile);
    },

    /**
     * Renders quantitative data with the form [x, value] and assumes data is equally spaced across
     * chromosome. Attachs a dict with track and chrom name information to DOM element.
     */
    _render_chrom_data: function (svg, chrom_arc, chrom_data) {
        var path_data = this._get_path_function(chrom_arc, chrom_data);

        if (!path_data) {
            return null;
        }

        // There is path data, so render as path.
        var parent = svg.datum(chrom_data.data);

        var path = parent
            .append("path")
            .attr("class", "chrom-data")
            .attr("chrom", chrom_arc.data.chrom)
            .attr("d", path_data);

        return path;
    },

    /**
     * Returns function for creating a path across the chrom arc.
     */
    _get_path_function: function (chrom_arc, chrom_data) {
        // If no chrom data, return null.
        if (typeof chrom_data === "string" || !chrom_data.data || chrom_data.data.length === 0) {
            return null;
        }

        // Radius scaler.
        var radius = d3.scale.linear().domain(this.data_bounds).range(this.radius_bounds).clamp(true);

        // Scaler for placing data points across arc.
        var angle = d3.scale
            .linear()
            .domain([0, chrom_data.data.length])
            .range([chrom_arc.startAngle, chrom_arc.endAngle]);

        // Use line generator to create area.
        var line = d3.svg.line
            .radial()
            .interpolate("linear")
            .radius((d) => radius(d[1]))
            .angle((d, i) => angle(i));

        return d3.svg.area
            .radial()
            .interpolate(line.interpolate())
            .innerRadius(radius(0))
            .outerRadius(line.radius())
            .angle(line.angle());
    },

    /**
     * Render track min, max using ticks.
     */
    render_labels: function () {
        var self = this;

        var // Keep counter of visible chroms.
            textTransform = () => "rotate(90)";

        // FIXME:
        // (1) using min_max class below is needed for _update_min_max, which could be improved.
        // (2) showing config on tick click should be replaced by proper track config icon.

        // Draw min, max on first chrom only.
        var ticks = this.drawTicks(
            this.parent_elt,
            [this.chroms_layout[0]],
            this._data_bounds_ticks_fn(),
            textTransform,
            true
        ).classed("min_max", true);

        // Show config when ticks are clicked on.
        _.each(ticks, (tick) => {
            $(tick).click(() => {
                var view = new config.ConfigSettingCollectionView({
                    collection: self.track.get("config"),
                });
                view.render_in_modal("Configure Track");
            });
        });

        /*
        // Filter for visible chroms, then for every third chrom so that labels attached to only every
        // third chrom.
        var visibleChroms = _.filter(this.chroms_layout, function(c) { return c.endAngle - c.startAngle > 0.08; }),
            labeledChroms = _.filter(visibleChroms, function(c, i) { return i % 3 === 0; });
        this.drawTicks(this.parent_elt, labeledChroms, this._data_bounds_ticks_fn(), textTransform, true);
        */
    },

    /**
     * Transition labels to new values (e.g new radius or data bounds).
     */
    _transition_labels: function () {
        // FIXME: (a) pull out function for getting labeled chroms? and (b) function used in transition below
        // is copied from UseTicks mixin, so pull out and make generally available.

        // If there are no data bounds, nothing to transition.
        if (this.data_bounds.length === 0) {
            return;
        }

        // Transition labels to new radius bounds.
        var self = this;

        var visibleChroms = _.filter(this.chroms_layout, (c) => c.endAngle - c.startAngle > 0.08);

        var labeledChroms = _.filter(visibleChroms, (c, i) => i % 3 === 0);

        var new_data = _.flatten(_.map(labeledChroms, (c) => self._data_bounds_ticks_fn()(c)));

        this.parent_elt
            .selectAll("g.tick")
            .data(new_data)
            .transition()
            .attr("transform", (d) => `rotate(${(d.angle * 180) / Math.PI - 90})translate(${d.radius},0)`);
    },

    /**
     * Get function for locating data bounds ticks.
     */
    _data_bounds_ticks_fn: function () {
        // Closure vars.
        var self = this;

        // Return function for locating ticks based on chrom arc data.
        return (
            d // Set up data to display min, max ticks.
        ) => [
            {
                radius: self.radius_bounds[0],
                angle: d.startAngle,
                label: self.formatNum(self.data_bounds[0]),
            },
            {
                radius: self.radius_bounds[1],
                angle: d.startAngle,
                label: self.formatNum(self.data_bounds[1]),
            },
        ];
    },

    /**
     * Returns an array with two values denoting the minimum and maximum
     * values for the track.
     */
    get_data_bounds: function (data) {},
});
_.extend(CircsterQuantitativeTrackView.prototype, UsesTicks);

/**
 * Bigwig track view in Circster.
 */
var CircsterBigWigTrackView = CircsterQuantitativeTrackView.extend({
    get_data_bounds: function (data) {
        // Set max across dataset by extracting all values, flattening them into a
        // single array, and getting third quartile.
        var values = _.flatten(
            _.map(data, (d) => {
                if (d) {
                    // Each data point has the form [position, value], so return all values.
                    return _.map(
                        d.data,
                        (
                            p // Null is used for a lack of data; resolve null to 0 for comparison.
                        ) => parseInt(p[1], 10) || 0
                    );
                } else {
                    return 0;
                }
            })
        );

        // For max, use 98% quantile in attempt to avoid very large values. However, this max may be 0
        // for sparsely populated data, so use max in that case.
        return [_.min(values), this._quantile(values, 0.98) || _.max(values)];
    },
});

/**
 * Chromosome interactions track view in Circster.
 */
var CircsterChromInteractionsTrackView = CircsterTrackView.extend({
    render: function () {
        var self = this;

        // When data is ready, render track.
        $.when(self.track.get("data_manager").data_is_ready()).then(() => {
            // When data has been fetched, render track.
            $.when(self.track.get("data_manager").get_genome_wide_data(self.genome)).then((genome_wide_data) => {
                var chord_data = [];
                var chroms_info = self.genome.get_chroms_info();
                // Convert chromosome data into chord data.
                _.each(genome_wide_data, (chrom_data, index) => {
                    // Map each interaction into chord data.
                    var cur_chrom = chroms_info[index].chrom;
                    var chrom_chord_data = _.map(chrom_data.data, (datum) => {
                        // Each datum is an interaction/chord.
                        var source_angle = self._get_region_angle(cur_chrom, datum[1]);

                        var target_angle = self._get_region_angle(datum[3], datum[4]);

                        return {
                            source: {
                                startAngle: source_angle,
                                endAngle: source_angle + 0.01,
                            },
                            target: {
                                startAngle: target_angle,
                                endAngle: target_angle + 0.01,
                            },
                        };
                    });

                    chord_data = chord_data.concat(chrom_chord_data);
                });

                self.parent_elt
                    .append("g")
                    .attr("class", "chord")
                    .selectAll("path")
                    .data(chord_data)
                    .enter()
                    .append("path")
                    .style("fill", self.get_fill_color())
                    .attr("d", d3.svg.chord().radius(self.radius_bounds[0]))
                    .style("opacity", 1);
            });
        });
    },

    update_radius_bounds: function (radius_bounds) {
        this.radius_bounds = radius_bounds;
        this.parent_elt.selectAll("path").transition().attr("d", d3.svg.chord().radius(this.radius_bounds[0]));
    },

    /**
     * Returns radians for a genomic position.
     */
    _get_region_angle: function (chrom, position) {
        // Find chrom angle data
        var chrom_angle_data = _.find(this.chroms_layout, (chrom_layout) => chrom_layout.data.chrom === chrom);

        // Return angle at position.
        return (
            chrom_angle_data.endAngle -
            ((chrom_angle_data.endAngle - chrom_angle_data.startAngle) * (chrom_angle_data.data.len - position)) /
                chrom_angle_data.data.len
        );
    },
});

// circster app loader
var Circster = Backbone.View.extend({
    initialize: function () {
        // load css
        mod_utils.cssLoadFile("static/style/circster.css");
        // -- Configure visualization --
        var genome = new visualization.Genome(window.galaxy_config.app.genome);

        var vis = new visualization.GenomeVisualization(window.galaxy_config.app.viz_config);

        // Add Circster-specific config options.
        vis.get("config").add([
            {
                key: "arc_dataset_height",
                label: "Arc Dataset Height",
                type: "int",
                value: 25,
                view: "circster",
            },
            {
                key: "track_gap",
                label: "Gap Between Tracks",
                type: "int",
                value: 5,
                view: "circster",
            },
            {
                key: "total_gap",
                label: "Gap [0-1]",
                type: "float",
                value: 0.4,
                view: "circster",
                hidden: true,
            },
        ]);

        var viz_view = new CircsterView({
            // view pane
            el: $("#center .unified-panel-body"),
            genome: genome,
            model: vis,
        });

        // Render vizualization
        viz_view.render();

        // setup title
        $("#center .unified-panel-header-inner").append(
            `${window.galaxy_config.app.viz_config.title} ${window.galaxy_config.app.viz_config.dbkey}`
        );

        // setup menu
        var menu = mod_icon_btn.create_icon_buttons_menu(
            [
                {
                    icon_class: "plus-button",
                    title: _l("Add tracks"),
                    on_click: function () {
                        visualization.select_datasets({ dbkey: vis.get("dbkey") }, (tracks) => {
                            vis.add_tracks(tracks);
                        });
                    },
                },
                {
                    icon_class: "gear",
                    title: _l("Settings"),
                    on_click: function () {
                        var view = new config.ConfigSettingCollectionView({
                            collection: vis.get("config"),
                        });
                        view.render_in_modal("Configure Visualization");
                    },
                },
                {
                    icon_class: "disk--arrow",
                    title: _l("Save"),
                    on_click: function () {
                        const Galaxy = getGalaxyInstance();

                        // show saving dialog box
                        Galaxy.modal.show({
                            title: _l("Saving..."),
                            body: "progress",
                        });

                        // send to server
                        $.ajax({
                            url: `${getAppRoot()}visualization/save`,
                            type: "POST",
                            dataType: "json",
                            data: {
                                id: vis.get("vis_id"),
                                title: vis.get("title"),
                                dbkey: vis.get("dbkey"),
                                type: "trackster",
                                vis_json: JSON.stringify(vis),
                            },
                        })
                            .success((vis_info) => {
                                Galaxy.modal.hide();
                                vis.set("vis_id", vis_info.vis_id);
                            })
                            .error(() => {
                                // show dialog
                                Galaxy.modal.show({
                                    title: _l("Could Not Save"),
                                    body: "Could not save visualization. Please try again later.",
                                    buttons: {
                                        Cancel: function () {
                                            Galaxy.modal.hide();
                                        },
                                    },
                                });
                            });
                    },
                },
                {
                    icon_class: "cross-circle",
                    title: _l("Close"),
                    on_click: function () {
                        window.top.location = `${getAppRoot()}visualizations/list`;
                    },
                },
            ],
            { tooltip_config: { placement: "bottom" } }
        );

        // add menu
        menu.$el.attr("style", "float: right");
        $("#center .unified-panel-header-inner").append(menu.$el);

        // manual tooltip config because default gravity is S and cannot be changed
        $(".menu-button").tooltip({ placement: "bottom" });
    },
});

// Module exports.
export default {
    GalaxyApp: Circster,
};
