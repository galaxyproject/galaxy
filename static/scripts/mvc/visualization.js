/**
 * Model, view, and controller objects for Galaxy tools and tool panel.
 *
 * Models have no references to views, instead using events to indicate state 
 * changes; this is advantageous because multiple views can use the same object 
 * and models can be used without views.
 */
 
/**
 * -- Models --
 */
 
/**
 * A genome build.
 */
var Genome = Backbone.Model.extend({
    defaults: {
        name: null,
        key: null,
        chroms_info: null
    },
    
    get_chroms_info: function() {
        return this.attributes.chroms_info.chrom_info;  
    }
});

/**
 * A histogram dataset.
 */
var HistogramDataset = Backbone.Model.extend({
    
    initialize: function(data) {
        // Set max across dataset.
        this.attributes.data = data;
        this.attributes.max = _.max(data, function(d) { 
            if (!d || typeof d === "string") { return 0; }
            return d[1];
        })[1];
    }
    
});

/**
 * Layout for a histogram dataset in a circos visualization.
 */
var CircosHistogramDatasetLayout = Backbone.Model.extend({
    // TODO: should accept genome and dataset and use these to generate layout data.
    
    /**
     * Returns arc layouts for genome's chromosomes/contigs. Arcs are arranged in a circle 
     * separated by gaps.
     */
    chroms_layout: function() {
        // Setup chroms layout using pie.
        var chroms_info = this.attributes.genome.get_chroms_info(),
            pie_layout = d3.layout.pie().value(function(d) { return d.len; }).sort(null),
            init_arcs = pie_layout(chroms_info),
            gap_per_chrom = this.attributes.total_gap / chroms_info.length,
            chrom_arcs = _.map(init_arcs, function(arc, index) {
                // For short chroms, endAngle === startAngle.
                var new_endAngle = arc.endAngle - gap_per_chrom;
                arc.endAngle = (new_endAngle > arc.startAngle ? new_endAngle : arc.startAngle);
                return arc;
            });
            
            // TODO: remove arcs for chroms that are too small and recompute?
            
        return chrom_arcs;
    },
    
    /**
     * Returns layouts for drawing a chromosome's data. For now, only works with summary tree data.
     */
    chrom_data_layout: function(chrom_arc, chrom_data, inner_radius, outer_radius, max) {             
        // If no chrom data, return null.
        if (!chrom_data || typeof chrom_data === "string") {
            return null;
        }
        
        var data = chrom_data[0],
            delta = chrom_data[3],
            scale = d3.scale.linear()
                .domain( [0, max] )
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
 * -- Views --
 */
 
var CircosView = Backbone.View.extend({
    className: 'circos',
    
    initialize: function(options) {
        this.width = options.width;
        this.height = options.height;
        this.total_gap = options.total_gap;
        this.genome = options.genome;
        this.dataset = options.dataset;
        this.radius_start = options.radius_start;
        this.dataset_arc_height = options.dataset_arc_height;
    },
    
    render: function() {
        // -- Layout viz. --
        
        var radius_start = this.radius_start,
            dataset_arc_height = this.dataset_arc_height,
            
            // Layout chromosome arcs.
            arcs_layout = new CircosHistogramDatasetLayout({
                genome: this.genome,
                total_gap: this.total_gap
            }),
            chrom_arcs = arcs_layout.chroms_layout(),
            
            // Merge chroms layout with data.
            layout_and_data = _.zip(chrom_arcs, this.dataset.attributes.data),
            dataset_max = this.dataset.attributes.max,
            
            // Do dataset layout for each chromosome's data using pie layout.
            chroms_data_layout = _.map(layout_and_data, function(chrom_info) {
                var chrom_arc = chrom_info[0],
                    chrom_data = chrom_info[1];
                return arcs_layout.chrom_data_layout(chrom_arc, chrom_data, radius_start, radius_start + dataset_arc_height, dataset_max);
            });      
        
        // -- Render viz. --
        
        var svg = d3.select(this.$el[0])
          .append("svg")
            .attr("width", this.width)
            .attr("height", this.height)
          .append("g")
            .attr("transform", "translate(" + this.width / 2 + "," + this.height / 2 + ")");

        // Draw background arcs for each chromosome.
        var base_arc = svg.append("g").attr("id", "inner-arc"),
            arc_gen = d3.svg.arc()
                .innerRadius(radius_start)
                .outerRadius(radius_start + dataset_arc_height),
            // Draw arcs.
            chroms_elts = base_arc.selectAll("#inner-arc>path")
                .data(chrom_arcs).enter().append("path")
                .attr("d", arc_gen)
                .style("stroke", "#ccc")
                .style("fill",  "#ccc")
                .append("title").text(function(d) { return d.data.chrom; });

        // For each chromosome, draw dataset.
        _.each(chroms_data_layout, function(chrom_layout) {
            if (!chrom_layout) { return; }

            var group = svg.append("g"),
                arc_gen = d3.svg.arc().innerRadius(radius_start),
                dataset_elts = group.selectAll("path")
                    .data(chrom_layout).enter().append("path")
                    .attr("d", arc_gen)
                    .style("stroke", "red")
                    .style("fill",  "red");
        });
    } 
});

/**
 * -- Routers --
 */

/**
 * Router for track browser.
 */
var TrackBrowserRouter = Backbone.Router.extend({    
    initialize: function(options) {
        this.view = options.view;
        
        // Can't put regular expression in routes dictionary.
        // NOTE: parentheses are used to denote parameters returned to callback.
        this.route(/([\w]+)$/, 'change_location');
        this.route(/([\w]+\:[\d,]+-[\d,]+)$/, 'change_location');
        
        // Handle navigate events from view.
        var self = this;
        self.view.on("navigate", function(new_loc) {
            self.navigate(new_loc);
        });
    },
    
    change_location: function(new_loc) {
        this.view.go_to(new_loc);
    }
});
