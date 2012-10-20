define(["libs/underscore", "libs/d3", "viz/visualization"], function(_, d3, visualization) {

var SVGUtils = Backbone.Model.extend({

    /**
     * Returns true if element is visible.
     */
    is_visible: function(svg_elt, svg) {
        var eltBRect = svg_elt.getBoundingClientRect(),
            svgBRect = $('svg')[0].getBoundingClientRect();

        if (// To the left of screen?
            eltBRect.right < 0 ||
            // To the right of screen?
            eltBRect.left > svgBRect.right ||
            // Above screen?
            eltBRect.bottom < 0 || 
            // Below screen?
            eltBRect.top > svgBRect.bottom) {
            return false;
        }
        return true;
    }

});

/**
 * A label track.
 */
var CircsterLabelTrack = Backbone.Model.extend({
    defaults: {
        prefs: {
            color: '#ccc'
        }
    }
});

/**
 * Renders a full circster visualization.
 */ 
var CircsterView = Backbone.View.extend({
    className: 'circster',
    
    initialize: function(options) {
        this.total_gap = options.total_gap;
        this.genome = options.genome;
        this.dataset_arc_height = options.dataset_arc_height;
        this.track_gap = 5;
        this.label_arc_height = 20;
        this.scale = 1;
        this.track_views = null;

        // When tracks added to/removed from model, update view.
        this.model.get('tracks').on('add', this.add_track, this);
        this.model.get('tracks').on('remove', this.remove_track, this);
    },

    /**
     * Returns a list of tracks' radius bounds.
     */
    get_tracks_bounds: function() {
        var dataset_arc_height = this.dataset_arc_height,
            min_dimension = Math.min(this.$el.width(), this.$el.height()),
            // Compute radius start based on model, will be centered 
            // and fit entirely inside element by default.
            radius_start = min_dimension / 2 - 
                            this.model.get('tracks').length * (this.dataset_arc_height + this.track_gap) -
                            (this.label_arc_height + this.track_gap),

            // Compute range of track starting radii.
            tracks_start_radii = d3.range(radius_start, min_dimension / 2, this.dataset_arc_height + this.track_gap);

        // Map from track start to bounds; for label track
        var self = this;
        return _.map(tracks_start_radii, function(radius) {
            return [radius, radius + self.dataset_arc_height];
        });
    },
    
    render: function() {
        var self = this,
            dataset_arc_height = this.dataset_arc_height,
            width = self.$el.width(),
            height = self.$el.height(),
            tracks = this.model.get('tracks'),
            tracks_bounds = this.get_tracks_bounds(),

            // Set up SVG element.
            svg = d3.select(self.$el[0])
              .append("svg")
                .attr("width", width)
                .attr("height", height)
                .attr("pointer-events", "all")
              // Set up zooming, dragging.
              .append('svg:g')
                .call(d3.behavior.zoom().on('zoom', function() {
                    // Do zoom, drag.
                    var scale = d3.event.scale;
                    svg.attr("transform",
                      "translate(" + d3.event.translate + ")" + 
                      " scale(" + scale + ")");

                    // Propagate scale changes to views.
                    if (self.scale !== scale) {
                        // Use timeout to wait for zooming/dragging to stop before rendering more detail.
                        if (self.zoom_drag_timeout) {
                            clearTimeout(self.zoom_drag_timeout);
                        }
                        self.zoom_drag_timeout = setTimeout(function() {
                            // Render more detail in tracks' visible elements.
                            _.each(self.track_views, function(view) {
                                view.update_scale(scale);
                            });
                        }, 400);
                    }
                }))
                .attr("transform", "translate(" + width / 2 + "," + height / 2 + ")")
              .append('svg:g').attr('class', 'tracks');
                

        // -- Render each dataset in the visualization. --

        // Create a view for each track in the visualiation and render.
        this.track_views = tracks.map(function(track, index) {
            track_view_class = (track.get('track_type') === 'LineTrack' ? 
                                    CircsterBigWigTrackView : 
                                    CircsterSummaryTreeTrackView );
            
            return new track_view_class({
                el: svg.append('g')[0],
                track: track,
                radius_bounds: tracks_bounds[index],
                genome: self.genome,
                total_gap: self.total_gap
            });
        });

        _.each(this.track_views, function(view) {
            view.render();
        });

        // -- Render chromosome labels. --
        
        // Set radius start = end for track bounds.
        var track_bounds = tracks_bounds[tracks.length];
        track_bounds[1] = track_bounds[0];
        this.label_track_view = new CircsterLabelTrackView({
            el: svg.append('g')[0],
            track: new CircsterLabelTrack(),
            radius_bounds: track_bounds,
            genome: self.genome,
            total_gap: self.total_gap
        });
        
        this.label_track_view.render();
    },

    /**
     * Render a single track on the outside of the current visualization.
     */
    add_track: function(new_track) {
        // Recompute and update track bounds.
        var new_track_bounds = this.get_tracks_bounds();
        _.each(this.track_views, function(track_view, i) {
            //console.log(self.get_tracks_bounds(), i);
            track_view.update_radius_bounds(new_track_bounds[i]);
        });

        // Render new track.
        var track_index = this.track_views.length
            track_view_class = (new_track.get('track_type') === 'LineTrack' ? 
                                    CircsterBigWigTrackView : 
                                    CircsterSummaryTreeTrackView ),
            track_view = new track_view_class({
                el: d3.select('g.tracks').append('g')[0],
                track: new_track,
                radius_bounds: new_track_bounds[track_index],
                genome: this.genome,
                total_gap: this.total_gap
            });
        track_view.render();
        this.track_views.push(track_view);

        // Update label track.
        var track_bounds = new_track_bounds[ new_track_bounds.length-1 ];
        track_bounds[1] = track_bounds[0];
        this.label_track_view.update_radius_bounds(track_bounds);
    },

    /**
     * Remove a track from the view.
     */
    remove_track: function(track, tracks, options) {
        // -- Remove track from view. --
        var track_view = this.track_views[options.index];
        this.track_views.splice(options.index, 1);
        track_view.$el.remove();
        
        // Recompute and update track bounds.
        var new_track_bounds = this.get_tracks_bounds();
        _.each(this.track_views, function(track_view, i) {
            //console.log(self.get_tracks_bounds(), i);
            track_view.update_radius_bounds(new_track_bounds[i]);
        });
    }
});

/**
 * Renders a track in a Circster visualization.
 */
var CircsterTrackView = Backbone.View.extend({
    tagName: 'g',

    /* ----------------------- Public Methods ------------------------- */

    initialize: function(options) {
        this.options = options;
        this.options.bg_stroke = 'ccc';
        // Fill color when loading data.
        this.options.loading_bg_fill = '000';
        // Fill color when data has been loaded.
        this.options.bg_fill = 'ccc';
        this.options.chroms_layout = this._chroms_layout();
        this.options.data_bounds = [];
        this.options.scale = 1;
        this.options.parent_elt = d3.select(this.$el[0]);
    },

    /**
     * Render track's data by adding SVG elements to parent.
     */
    render: function() {
        // -- Create track group element. --
        var track_parent_elt = this.options.parent_elt;

        if (!track_parent_elt) {
            console.log('no parent elt');
        }

        // -- Render background arcs. --
        var genome_arcs = this.options.chroms_layout,
            arc_gen = d3.svg.arc()
                        .innerRadius(this.options.radius_bounds[0])
                        .outerRadius(this.options.radius_bounds[1]),

            // Attach data to group element.
            chroms_elts = track_parent_elt.selectAll('g')
                .data(genome_arcs).enter().append('svg:g'),

            // Draw chrom arcs/paths.
            chroms_paths = chroms_elts.append('path')
                .attr("d", arc_gen)
                .attr('class', 'chrom-background')
                .style("stroke", this.options.bg_stroke)
                .style("fill",  this.options.loading_bg_fill);

            // Append titles to paths.
            chroms_paths.append("title").text(function(d) { return d.data.chrom; });
            
        // -- Render track data and, when track data is rendered, apply preferences and update chrom_elts fill. --

        var self = this,
            data_manager = self.options.track.get('data_manager'),
            // If track has a data manager, get deferred that resolves when data is ready.
            data_ready_deferred = (data_manager ? data_manager.data_is_ready() : true );

        // When data is ready, render track.
        $.when(data_ready_deferred).then(function() {
            $.when(self._render_data(track_parent_elt)).then(function() {
                chroms_paths.style("fill", self.options.bg_fill);
            });
        });
    },

    /**
     * Update radius bounds.
     */
    update_radius_bounds: function(radius_bounds) {
        // Update bounds.
        this.options.radius_bounds = radius_bounds;

        // -- Update background arcs. --
        var new_d = d3.svg.arc()
                        .innerRadius(this.options.radius_bounds[0])
                        .outerRadius(this.options.radius_bounds[1]);
        
        this.options.parent_elt.selectAll('g>path.chrom-background').transition().duration(1000).attr('d', new_d);

        this._transition_chrom_data();
    },

    /**
     * Update view scale. This fetches more data if scale is increased.
     */
    update_scale: function(new_scale) {
        // -- Update scale and return if new scale is less than old scale. --

        var old_scale = this.options.scale;
        this.options.scale = new_scale;
        if (new_scale <= old_scale) {
            return;
        }

        // -- Scale increased, so render visible data with more detail. --
        
        var self = this,
            utils = new SVGUtils();

        // Select all chrom data and filter to operate on those that are visible.
        this.options.parent_elt.selectAll('path.chrom-data').filter(function(d, i) {
            return utils.is_visible(this);
        }).each(function(d, i) {
            // Now operating on a single path element representing chromosome data.
            var path_elt = d3.select(this),
                chrom = path_elt.attr('chrom'),
                chrom_region = self.options.genome.get_chrom_region(chrom),

                // Get more detailde data for chrom.
                data_deferred = self.options.track.get('data_manager').get_more_detailed_data(chrom_region, 'Coverage', 0, new_scale);

            // When more data is available, use new data to redraw path.
            $.when(data_deferred).then(function(data) {
                // Remove current data path.
                path_elt.remove();
                
                // Update data bounds with new data.
                self._update_data_bounds();

                // Find chromosome arc to draw data on.
                var chrom_arc = _.find(self.options.chroms_layout, function(layout) { 
                        return layout.data.chrom === chrom; 
                });

                // Add new data path and apply preferences.
                var prefs = self.options.track.get('prefs'),
                    block_color = prefs.block_color;
                if (!block_color) { block_color = prefs.color; }
                self._render_chrom_data(self.options.parent_elt, chrom_arc, data).style('stroke', block_color).style('fill', block_color);
            });
        });

        return self;
    },

    /* ----------------------- Internal Methods ------------------------- */

    /**
     * Transitions chrom data to new values (e.g new radius or data bounds).
     */
    _transition_chrom_data: function() {
        var track = this.options.track,
            chrom_arcs = this.options.chroms_layout,
            chrom_data_paths = this.options.parent_elt.selectAll('g>path.chrom-data'),
            num_paths = chrom_data_paths[0].length;

        if (num_paths > 0) {
            var self = this;
            $.when(track.get('data_manager').get_genome_wide_data(this.options.genome)).then(function(genome_wide_data) {
                // Map chrom data to path data, filtering out null values.
                var path_data = _.reject( _.map(genome_wide_data, function(chrom_data, i) {
                    var rval = null,
                        path_fn = self._get_path_function(chrom_arcs[i], chrom_data);
                    if (path_fn) {
                        rval = path_fn(chrom_data.data);
                    }
                    return rval;
                }), function(p_data) { return p_data === null; } );

                // Transition each path.
                chrom_data_paths.each(function(path, index) {
                    d3.select(this).transition().duration(1000).attr('d', path_data[index]);
                });
                
            });
        }
    },

    /**
     * Update data bounds.
     */
    _update_data_bounds: function() {
        var old_bounds = this.options.data_bounds;
        this.options.data_bounds = this.get_data_bounds(this.options.track.get('data_manager').get_genome_wide_data(this.options.genome));

        // If bounds have changed, transition all paths to use the new data bounds.
        if (this.options.data_bounds[0] < old_bounds[0] || this.options.data_bounds[1] > old_bounds[1]) {
            this._transition_chrom_data();
        }
    },

    /**
     * Render data as elements attached to svg.
     */
    _render_data: function(svg) {
        var self = this,
            chrom_arcs = this.options.chroms_layout,
            track = this.options.track,
            rendered_deferred = $.Deferred();

        // When genome-wide data is available, render data.
        $.when(track.get('data_manager').get_genome_wide_data(this.options.genome)).then(function(genome_wide_data) {
            // Set bounds.
            self.options.data_bounds = self.get_data_bounds(genome_wide_data);

            // Merge chroms layout with data.
            layout_and_data = _.zip(chrom_arcs, genome_wide_data),

            // Render each chromosome's data.
            chroms_data_layout = _.map(layout_and_data, function(chrom_info) {
                var chrom_arc = chrom_info[0],
                    data = chrom_info[1];
                return self._render_chrom_data(svg, chrom_arc, data);
            });

            // Apply prefs to all track data.
            var config = track.get('config'),
                block_color = config.get_value('block_color');;
            if (!block_color) { block_color = config.get_value('color'); }
            self.options.parent_elt.selectAll('path.chrom-data').style('stroke', block_color).style('fill', block_color);

            rendered_deferred.resolve(svg);
        });

        return rendered_deferred;
    },

    /**
     * Render a chromosome data and attach elements to svg.
     */
    _render_chrom_data: function(svg, chrom_arc, data) {},

    /**
     * Returns data for creating a path for the given data using chrom_arc and data bounds.
     */
    _get_path_function: function(chrom_arc, chrom_data) {},

    /**
     * Returns arc layouts for genome's chromosomes/contigs. Arcs are arranged in a circle 
     * separated by gaps.
     */
    _chroms_layout: function() {
        // Setup chroms layout using pie.
        var chroms_info = this.options.genome.get_chroms_info(),
            pie_layout = d3.layout.pie().value(function(d) { return d.len; }).sort(null),
            init_arcs = pie_layout(chroms_info),
            gap_per_chrom = this.options.total_gap / chroms_info.length,
            chrom_arcs = _.map(init_arcs, function(arc, index) {
                // For short chroms, endAngle === startAngle.
                var new_endAngle = arc.endAngle - gap_per_chrom;
                arc.endAngle = (new_endAngle > arc.startAngle ? new_endAngle : arc.startAngle);
                return arc;
            });
        return chrom_arcs;
    }
});

/**
 * Render chromosome labels.
 */
var CircsterLabelTrackView = CircsterTrackView.extend({

    initialize: function(options) {
        CircsterTrackView.prototype.initialize.call(this, options);
        this.options.bg_stroke = 'fff';
        this.options.bg_fill = 'fff';
    },

    /**
     * Render labels.
     */
    _render_data: function(svg) {
        // Add chromosome label where it will fit; an alternative labeling mechanism 
        // would be nice for small chromosomes.
        var chrom_arcs = svg.selectAll('g');

        chrom_arcs.selectAll('path')
            .attr('id', function(d) { return 'label-' + d.data.chrom; });
          
        chrom_arcs.append("svg:text")
            .filter(function(d) { 
                return d.endAngle - d.startAngle > 0.08;
            })
            .attr('text-anchor', 'middle')
          .append("svg:textPath")
            .attr("xlink:href", function(d) { return "#label-" + d.data.chrom; })
            .attr('startOffset', '25%')
            .text(function(d) { 
                return d.data.chrom;
            });
    }
});

/**
 * View for quantitative track in Circster.
 */
var CircsterQuantitativeTrackView = CircsterTrackView.extend({

    /**
     * Renders quantitative data with the form [x, value] and assumes data is equally spaced across
     * chromosome. Attachs a dict with track and chrom name information to DOM element.
     */
    _render_chrom_data: function(svg, chrom_arc, chrom_data) {
        var path_data = this._get_path_function(chrom_arc, chrom_data);

        if (!path_data) { return null; }

        // There is path data, so render as path.
        var parent = svg.datum(chrom_data.data),
            path = parent.append('path')
                         .attr('class', 'chrom-data')
                         .attr('chrom', chrom_arc.data.chrom)
                         .attr('d', path_data);

        return path;
    },

    /**
     * Returns function for creating a path across the chrom arc.
     */
    _get_path_function: function(chrom_arc, chrom_data) {
        // If no chrom data, return null.
        if (typeof chrom_data === "string" || !chrom_data.data || chrom_data.data.length === 0) {
            return null;
        }

        // Radius scaler.
        var radius = d3.scale.linear()
                       .domain(this.options.data_bounds)
                       .range(this.options.radius_bounds);

        // Scaler for placing data points across arc.
        var angle = d3.scale.linear()
            .domain([0, chrom_data.data.length])
            .range([chrom_arc.startAngle, chrom_arc.endAngle]);

        // Use line generator to create area.
        var line = d3.svg.line.radial()
            .interpolate("linear")
            .radius(function(d) { return radius(d[1]); })
            .angle(function(d, i) { return angle(i); });

        return d3.svg.area.radial()
            .interpolate(line.interpolate())
            .innerRadius(radius(0))
            .outerRadius(line.radius())
            .angle(line.angle());
    },

    /**
     * Returns an array with two values denoting the minimum and maximum
     * values for the track.
     */
    get_data_bounds: function(data) {}

});

/**
 * Layout for summary tree data in a circster visualization.
 */
var CircsterSummaryTreeTrackView = CircsterQuantitativeTrackView.extend({

    get_data_bounds: function(data) {
        // Get max across data.
        var max_data = _.map(data, function(d) {
            if (typeof d === 'string' || !d.max) { return 0; }
            return d.max;
        });
        return [ 0, (max_data && typeof max_data !== 'string' ? _.max(max_data) : 0) ];
    }
});

/**
 * Bigwig track view in Circster
 */
var CircsterBigWigTrackView = CircsterQuantitativeTrackView.extend({

    get_data_bounds: function(data) {
        // Set max across dataset by extracting all values, flattening them into a 
        // single array, and getting the min and max.
        var values = _.flatten( _.map(data, function(d) {
            if (d) {
                // Each data point has the form [position, value], so return all values.
                return _.map(d.data, function(p) {
                    return p[1];
                });
            }
            else {
                return 0;
            }
        }) );

        return [ _.min(values), _.max(values) ];
    }
});

// Module exports.
return {
    CircsterView: CircsterView
};

});
