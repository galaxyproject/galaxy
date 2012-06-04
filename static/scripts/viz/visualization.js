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
 * A genome browser bookmark.
 */
var BrowserBookmark = Backbone.Model.extend({
    defaults: {
        chrom: null,
        start: 0,
        end: 0,
        note: ""
    }
});

/**
 * Bookmarks collection.
 */
var BrowserBookmarks = Backbone.Collection.extend({
    model: BrowserBookmark
});

/**
 * A visualization.
 */
var Visualization = Backbone.RelationalModel.extend({
    defaults: {
        id: "",
        title: "",
        type: "",
        dbkey: "",
        datasets: []
    },
    
    url: function() { return galaxy_paths.get("visualization_url"); },
    
    /**
     * POSTs visualization's JSON to its URL using the parameter 'vis_json'
     * Note: This is necessary because (a) Galaxy requires keyword args and 
     * (b) Galaxy does not handle PUT now.
     */
    save: function() {
        return $.ajax({
            url: this.url(),
            type: "POST",
            dataType: "json",
            data: { 
                vis_json: JSON.stringify(this)
            }
        });
    }
});

/**
 * A Trackster visualization.
 */
var TracksterVisualization = Visualization.extend({
    defaults: {
        bookmarks: [],
        viewport: {}
    }
});

/**
 * A Circster visualization.
 */
var CircsterVisualization = Visualization.extend({
});

/**
 * A dataset. In Galaxy, datasets are associated with a history, so
 * this object is also known as a HistoryDatasetAssociation.
 */
var Dataset = Backbone.Model.extend({
    defaults: {
        id: "",
        type: "",
        name: "",
        hda_ldda: ""  
    } 
});

/**
 * A histogram dataset.
 */
var HistogramDataset = Backbone.Model.extend({
    /*
    defaults: {
        data: [],
        dataset: null,
        max: 0  
    },
    */
    
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
 * Configuration data for a Trackster track.
 */
var TrackConfig = Backbone.Model.extend({
    
});

/**
 * Layout for a histogram dataset in a circster visualization.
 */
var CircsterHistogramDatasetLayout = Backbone.Model.extend({
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
 
var CircsterView = Backbone.View.extend({
    className: 'circster',
    
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
            arcs_layout = new CircsterHistogramDatasetLayout({
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

/**
 * -- Helper functions.
 */
 
/**
 * Use a popup grid to add more datasets.
 */
var add_datasets = function(dataset_url, add_track_async_url, success_fn) {
    $.ajax({
        url: dataset_url,
        data: { "f-dbkey": view.dbkey },
        error: function() { alert( "Grid failed" ); },
        success: function(table_html) {
            show_modal(
                "Select datasets for new tracks",
                table_html, {
                    "Cancel": function() {
                        hide_modal();
                    },
                    "Add": function() {
                        var requests = [];
                        $('input[name=id]:checked,input[name=ldda_ids]:checked').each(function() {
                            var data,
                                id = $(this).val();
                                if ($(this).attr("name") === "id") {
                                    data = { hda_id: id };
                                } else {
                                    data = { ldda_id: id};
                                }
                                requests[requests.length] = $.ajax({
                                    url: add_track_async_url,
                                    data: data,
                                    dataType: "json",
                                });
                        });
                        // To preserve order, wait until there are definitions for all tracks and then add 
                        // them sequentially.
                        $.when.apply($, requests).then(function() {
                            // jQuery always returns an Array for arguments, so need to look at first element
                            // to determine whether multiple requests were made and consequently how to 
                            // map arguments to track definitions.
                            var track_defs = (arguments[0] instanceof Array ?  
                                               $.map(arguments, function(arg) { return arg[0]; }) :
                                               [ arguments[0] ]
                                               );
                            success_fn(track_defs);
                        });
                        hide_modal();
                    }
                }
            );
        }
    });
};
