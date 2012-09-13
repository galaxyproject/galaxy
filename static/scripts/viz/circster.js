define( ["libs/d3", "viz/visualization"], function( d3, visualization ) {

// General backbone style inheritence
var Base = function() { this.initialize && this.initialize.apply(this, arguments); }; Base.extend = Backbone.Model.extend;

/**
 * Renders a full circster visualization
 */ 
var CircsterView = Backbone.View.extend({
    className: 'circster',
    
    initialize: function(options) {
        this.total_gap = options.total_gap;
        this.genome = options.genome;
        this.dataset_arc_height = options.dataset_arc_height;
        this.track_gap = 5;
    },
    
    render: function() {
        var self = this,
            dataset_arc_height = this.dataset_arc_height,
            width = self.$el.width(),
            height = self.$el.height(),
            // Compute radius start based on model, will be centered 
            // and fit entirely inside element by default
            init_radius_start = ( Math.min(width,height)/2 - 
                                  this.model.get('tracks').length * (this.dataset_arc_height + this.track_gap) );

        // Set up SVG element.
        var svg = d3.select(self.$el[0])
              .append("svg")
                .attr("width", width)
                .attr("height", height)
                .attr("pointer-events", "all")
              // Set up zooming, dragging.
              .append('svg:g')
                .call(d3.behavior.zoom().on('zoom', function() {
                    svg.attr("transform",
                      "translate(" + d3.event.translate + ")" + 
                      " scale(" + d3.event.scale + ")");
                }))
                .attr("transform", "translate(" + width / 2 + "," + height / 2 + ")")
              .append('svg:g');
                

        // -- Render each dataset in the visualization. --
        this.model.get('tracks').each(function(track, index) {
            var dataset = track.get('genome_wide_data'),
                radius_start = init_radius_start + index * (dataset_arc_height + self.track_gap),
                track_renderer_class = (dataset instanceof visualization.GenomeWideBigWigData ? CircsterBigWigTrackRenderer : CircsterSummaryTreeTrackRenderer );

            var track_renderer = new track_renderer_class({
                track: track,
                radius_start: radius_start,
                radius_end: radius_start + dataset_arc_height,
                genome: self.genome,
                total_gap: self.total_gap
            });

            track_renderer.render( svg );

        });
    }
});

var CircsterTrackRenderer = Base.extend( {

    initialize: function( options ) {
        this.options = options;
    },

    render: function( svg ) {

        var genome_arcs = this.chroms_layout(),
            chroms_arcs = this.genome_data_layout();
            
        // -- Render. --

        // Draw background arcs for each chromosome.
        var radius_start = this.options.radius_start,
            radius_end = this.options.radius_end,
            base_arc = svg.append("g").attr("id", "inner-arc"),
            arc_gen = d3.svg.arc()
                .innerRadius(radius_start)
                .outerRadius(radius_end),
            // Draw arcs.
            chroms_elts = base_arc.selectAll("#inner-arc>path")
                .data(genome_arcs).enter().append("path")
                .attr("d", arc_gen)
                .style("stroke", "#ccc")
                .style("fill",  "#ccc")
                .append("title").text(function(d) { return d.data.chrom; });

        // For each chromosome, draw dataset.
        var prefs = this.options.track.get('prefs'),
            block_color = prefs.block_color;

        _.each(chroms_arcs, function(chrom_layout) {
            if (!chrom_layout) { return; }

            var group = svg.append("g"),
                arc_gen = d3.svg.arc().innerRadius(radius_start),
                dataset_elts = group.selectAll("path")
                    .data(chrom_layout).enter()
                    ;
                    //.style("stroke", block_color)
                    //.style("fill",  block_color)
            
            dataset_elts.append("path").attr("d", arc_gen).style("stroke",  block_color);
                
        });
    },

    /**
     * Returns arc layouts for genome's chromosomes/contigs. Arcs are arranged in a circle 
     * separated by gaps.
     */
    chroms_layout: function() {
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
     * Returns layouts for drawing a chromosome's data.
     */
    chrom_data_layout: function(chrom_arc, chrom_data, inner_radius, outer_radius, max) {
    },

    genome_data_layout: function() {
        var self = this,
            chrom_arcs = this.chroms_layout(),
            dataset = this.options.track.get('genome_wide_data'),
            r_start = this.options.radius_start,
            r_end = this.options.radius_end,
                
            // Merge chroms layout with data.
            layout_and_data = _.zip(chrom_arcs, dataset.get('data')),
            
            // Do dataset layout for each chromosome's data using pie layout.
            chroms_data_layout = _.map(layout_and_data, function(chrom_info) {
                var chrom_arc = chrom_info[0],
                    chrom_data = chrom_info[1];
                return self.chrom_data_layout(chrom_arc, chrom_data, r_start, r_end, dataset.get('min'), dataset.get('max'));
            });

        return chroms_data_layout;
    }
});

/**
 * Layout for summary tree data in a circster visualization.
 */
var CircsterSummaryTreeTrackRenderer = CircsterTrackRenderer.extend({
    
    /**
     * Returns layouts for drawing a chromosome's data.
     */
    chrom_data_layout: function(chrom_arc, chrom_data, inner_radius, outer_radius, min, max) {
        // If no chrom data, return null.
        if (!chrom_data || typeof chrom_data === "string") {
            return null;
        }
        
        var data = chrom_data[0],
            delta = chrom_data[3],
            scale = d3.scale.linear()
                .domain( [min, max] )
                .range( [inner_radius, outer_radius] ),       
            arc_layout = d3.layout.pie().value(function(d) {
                return delta;
            })
                .startAngle(chrom_arc.startAngle)
                .endAngle(chrom_arc.endAngle),
        arcs = arc_layout(data);
        
        // Use scale to assign outer radius.
        _.each(data, function(datum, index) {
            arcs[index].outerRadius = scale(datum[1]);
        });
        
        return arcs;
    }
});

/**
 * Layout for BigWig data in a circster visualization.
 */
var CircsterBigWigTrackRenderer = CircsterTrackRenderer.extend({

    /**
     * Returns layouts for drawing a chromosome's data.
     */
    chrom_data_layout: function(chrom_arc, chrom_data, inner_radius, outer_radius, min, max) {
        var data = chrom_data.data;
        if (data.length === 0) { return; }
        
        var scale = d3.scale.linear()
                .domain( [min, max] )
                .range( [inner_radius, outer_radius] ),
            arc_layout = d3.layout.pie().value(function(d, i) {
                // If at end of data, draw nothing.
                if (i + 1 === data.length) { return 0; }

                // Layout is from current position to next position.
                return data[i+1][0] - data[i][0];
            })
                .startAngle(chrom_arc.startAngle)
                .endAngle(chrom_arc.endAngle),
        arcs = arc_layout(data);
        
        // Use scale to assign outer radius.
        _.each(data, function(datum, index) {
            arcs[index].outerRadius = scale(datum[1]);
        });
        
        return arcs;
    }

});

return {
    CircsterView: CircsterView
};

});
