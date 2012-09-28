define(["libs/underscore", "libs/d3", "viz/visualization"], function(_, d3, visualization) {

// General backbone style inheritence
var Base = function() { this.initialize && this.initialize.apply(this, arguments); }; Base.extend = Backbone.Model.extend;

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
// FIXME: merge with tracks.js LabelTrack
var LabelTrack = Backbone.Model.extend({
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
    },
    
    render: function() {
        var self = this,
            dataset_arc_height = this.dataset_arc_height,
            width = self.$el.width(),
            height = self.$el.height(),
            // Compute radius start based on model, will be centered 
            // and fit entirely inside element by default.
            init_radius_start = Math.min(width, height) / 2 - 
                                this.model.get('tracks').length * (this.dataset_arc_height + this.track_gap) -
                                (this.label_arc_height + this.track_gap),
            tracks = this.model.get('tracks');

        // Set up SVG element.
        var svg = d3.select(self.$el[0])
              .append("svg")
                .attr("width", width)
                .attr("height", height)
                .attr("pointer-events", "all")
              // Set up zooming, dragging.
              .append('svg:g')
                .call(d3.behavior.zoom().on('zoom', function() {
                    // Do zoom.
                    svg.attr("transform",
                      "translate(" + d3.event.translate + ")" + 
                      " scale(" + d3.event.scale + ")");

                    // Update visible elements with more data.
                    var utils = new SVGUtils(),
                        tracks_and_chroms_to_update = {};

                    tracks.each(function(t) {
                        tracks_and_chroms_to_update[t.id] = [];
                    });

                    d3.selectAll('path.chrom-data').filter(function(d, i) {
                        return utils.is_visible(this, svg);
                    }).each(function(d, i) {
                        var elt_data = $.data(this, 'chrom_data');
                        tracks_and_chroms_to_update[elt_data.track.id].push(elt_data.chrom);
                    });

                    /*
                    _.each(_.pairs(tracks_and_chroms_to_update), function(track_and_chroms) {
                        var track = tracks.get(track_and_chroms[0])
                            chroms = track_and_chroms[1];

                        _.each(chroms, function(chr_name) {
                            var chr_region = self.genome.get_chrom_region(chr_name),
                                data_deferred = track.get('data_manager').get_more_detailed_data(chr_region, 'Coverage', 0, d3.event.scale);

                            $.when(data_deferred).then(function(data) {
                                console.log("got more detailed data", data);
                            })
                        })


                    });

                    // TODO: update tracks and chroms.
                    console.log(tracks_and_chroms_to_update);
                    */
                }))
                .attr("transform", "translate(" + width / 2 + "," + height / 2 + ")")
              .append('svg:g');
                

        // -- Render each dataset in the visualization. --
        tracks.each(function(track, index) {
            var radius_start = init_radius_start + index * (dataset_arc_height + self.track_gap),
                track_renderer_class = (track.get('track_type') === 'LineTrack' ? 
                                        CircsterBigWigTrackRenderer : 
                                        CircsterSummaryTreeTrackRenderer );

            var track_renderer = new track_renderer_class({
                track: track,
                track_index: index, 
                radius_start: radius_start,
                radius_end: radius_start + dataset_arc_height,
                genome: self.genome,
                total_gap: self.total_gap
            });

            track_renderer.render(svg);

        });

        // -- Render chromosome labels. --
        var radius_start = init_radius_start + tracks.length * (dataset_arc_height + self.track_gap) + self.track_gap;
        var chrom_labels_track = new CircsterLabelTrackRenderer({
            track: new LabelTrack(),
            track_index: tracks.length,
            radius_start: radius_start,
            radius_end: radius_start,
            genome: self.genome,
            total_gap: self.total_gap
        });

        chrom_labels_track.render(svg);
    }
});

var CircsterTrackRenderer = Base.extend( {

    initialize: function(options) {
        this.options = options;
        this.options.bg_stroke = 'ccc';
        this.options.bg_fill = 'ccc';
    },

    render: function(svg) {
        // Create track group element.
        var track_group_elt = svg.append("g").attr("id", "parent-" + this.options.track_index);

        // Render background arcs.
        var genome_arcs = this._chroms_layout(),
            radius_start = this.options.radius_start,
            radius_end = this.options.radius_end,
            arc_gen = d3.svg.arc()
                        .innerRadius(radius_start)
                        .outerRadius(radius_end),

            chroms_elts = track_group_elt.selectAll('g')
                .data(genome_arcs).enter().append('svg:g');

        // Draw arcs.
        chroms_elts.append("path")
            .attr("d", arc_gen)
            .style("stroke", this.options.bg_stroke)
            .style("fill",  this.options.bg_fill)
            .append("title").text(function(d) { return d.data.chrom; });
            
        // Render track data.
        this.render_data(track_group_elt);

        // Apply prefs.
        var prefs = this.options.track.get('prefs'),
            block_color = prefs.block_color;
        if (!block_color) { block_color = prefs.color; }
        track_group_elt.selectAll('path.chrom-data').style('stroke', block_color).style('fill', block_color);
    },

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
    },

    /**
     * Render chromosome data and attach elements to svg.
     */
    render_chrom_data: function(svg, chrom_arc, data, inner_radius, outer_radius, max) {
    },

    /**
     * Render data as elements attached to svg.
     */
    render_data: function(svg) {
        var self = this,
            chrom_arcs = this._chroms_layout(),
            track = this.options.track,
            r_start = this.options.radius_start,
            r_end = this.options.radius_end,

            genome_wide_data = track.get_genome_wide_data(this.options.genome),
                
            // Merge chroms layout with data.
            layout_and_data = _.zip(chrom_arcs, genome_wide_data),

            // Get min, max in data.
            bounds = this.get_bounds(genome_wide_data),
            
            // Do dataset layout for each chromosome's data using pie layout.
            chroms_data_layout = _.map(layout_and_data, function(chrom_info) {
                var chrom_arc = chrom_info[0],
                    data = chrom_info[1];
                return self.render_chrom_data(svg, chrom_arc, data, 
                                              r_start, r_end, 
                                              bounds.min, bounds.max);
            });

        return chroms_data_layout;
    }
});

/**
 * Render chromosome labels.
 */
var CircsterLabelTrackRenderer = CircsterTrackRenderer.extend({

    initialize: function(options) {
        this.options = options;
        this.options.bg_stroke = 'fff';
        this.options.bg_fill = 'fff';
    },

    /**
     * Render labels.
     */
    render_data: function(svg) {
        // Add chromosome label where it will fit; an alternative labeling mechanism 
        // would be nice for small chromosomes.
        var chrom_arcs = svg.selectAll('g');

        chrom_arcs.selectAll('path')
            .attr('id', function(d) { return 'label-' + d.data.chrom; })
          
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
 * Rendered for quantitative data.
 */
var CircsterQuantitativeTrackRenderer = CircsterTrackRenderer.extend({

    /**
     * Renders quantitative data with the form [x, value] and assumes data is equally spaced across
     * chromosome. Attachs a dict with track and chrom name information to DOM element.
     */
    render_quantitative_data: function(svg, chrom_arc, data, inner_radius, outer_radius, min, max) {
        // Radius scaler.
        var radius = d3.scale.linear()
                       .domain([min, max])
                       .range([inner_radius, outer_radius]);

        // Scaler for placing data points across arc.
        var angle = d3.scale.linear()
            .domain([0, data.length])
            .range([chrom_arc.startAngle, chrom_arc.endAngle]);

        var line = d3.svg.line.radial()
            .interpolate("linear")
            .radius(function(d) { return radius(d[1]); })
            .angle(function(d, i) { return angle(i); });

        var area = d3.svg.area.radial()
            .interpolate(line.interpolate())
            .innerRadius(radius(0))
            .outerRadius(line.radius())
            .angle(line.angle());

        // Render data.
        var parent = svg.datum(data),                    
            path = parent.append("path")
                         .attr("class", "chrom-data")
                         .attr("d", area);

        // Attach dict with track and chrom info for path.
        $.data(path[0][0], "chrom_data", {
            track: this.options.track,
            chrom: chrom_arc.data.chrom
        });
    },

    /**
     * Returns an object with min, max attributes denoting the minimum and maximum
     * values for the track.
     */
    get_bounds: function() {}

});

/**
 * Layout for summary tree data in a circster visualization.
 */
var CircsterSummaryTreeTrackRenderer = CircsterQuantitativeTrackRenderer.extend({
    
    /**
     * Renders a chromosome's data.
     */
    render_chrom_data: function(svg, chrom_arc, chrom_data, inner_radius, outer_radius, min, max) {
        // If no chrom data, return null.
        if (!chrom_data || typeof chrom_data === "string") {
            return null;
        }

        return this.render_quantitative_data(svg, chrom_arc, chrom_data.data, inner_radius, outer_radius, min, max);
    },

    get_bounds: function(data) {
        // Get max across data.
        var max_data = _.map(data, function(d) {
            if (!d || typeof d === 'string') { return 0; }
            return d.max;
        });
        return {
            min: 0,
            max: (max_data && typeof max_data !== 'string' ? _.max(max_data) : 0)
        };
    }
});

/**
 * Layout for BigWig data in a circster visualization.
 */
var CircsterBigWigTrackRenderer = CircsterQuantitativeTrackRenderer.extend({
    
    /**
     * Renders a chromosome's data.
     */
    render_chrom_data: function(svg, chrom_arc, chrom_data, inner_radius, outer_radius, min, max) {
        var data = chrom_data.data;
        if (data.length === 0) { return; }

        return this.render_quantitative_data(svg, chrom_arc, data, inner_radius, outer_radius, min, max);
    },

    get_bounds: function(data) {
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

        return {
            min: _.min(values),
            max: _.max(values)
        };
    }
});

return {
    CircsterView: CircsterView
};

});
