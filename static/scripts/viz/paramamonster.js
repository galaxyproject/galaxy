/**
 * Visualization and components for ParamaMonster, a visualization for exploring a tool's parameter space via 
 * genomic visualization.
 */
 
/**
 * --- Models ---
 */
 
var ToolParameterTree = Backbone.Model.extend({
    defaults: {
        tool: null,
        params: null,
        num_samples: 4
    },
    
    
    initialize: function(options) {
        //
        // -- Create tree data from tool. --
        //
        
        // Valid inputs for tree are number, select parameters.
        var tool = this.get('tool'),
            num_samples = this.get('num_samples'),
            params_samples = tool.get('inputs').map(function(input) {
                return input.get_samples(num_samples);
            }),
            filtered_params_samples = _.filter(params_samples, function(param_sample) {
                return param_sample.get('samples').length !== 0;
            });
            
        /**
         * Returns tree data. Params_sampling is an array of  
         * 
         */
        var create_tree_data = function(params_samples, index) {
            var 
                param_samples = params_samples[index],
                param = param_samples.get('param'),
                param_name = param.get('name'),
                settings = param_samples.get('samples');

            // Create leaves when last parameter setting is reached.
            if (params_samples.length - 1 === index) {
                return _.map(settings, function(setting) {
                    return {
                        name: param_name + '=' + setting,
                        param: param
                    }
                });
            }
            
            // Recurse to handle other parameters.
            return _.map(settings, function(setting) {
                 return {
                     name: param_name + '=' + setting,
                     param: param,
                     children: create_tree_data(filtered_params_samples, index + 1)
                 }
            });       
        };
        
        var tree_data = {
            name: 'Parameter Tree for ' + tool.get('name'),
            children: create_tree_data(filtered_params_samples, 0)
        };
            
        // Set valid inputs, tree data for later use.
        this.set('params', _.map(params_samples, function(s) { return s.get('param') }));
        this.set('tree_data', tree_data);
    }
    
});

/**
 * Tile of rendered genomic data.
 */ 
var Tile = Backbone.Model.extend({
    defaults: {
        track: null,
        index: null,
        region: null,
        resolution: null,
        data: null,
        stale: null,
        html_elt: null
    },
    
    initialize: function(options) {
        
    }
    
});

/**
 * A track in a genome browser.
 */
var Track = Backbone.Model.extend({
    defaults: {
        dataset: null
    }
});

var FeatureTrack = Track.extend({
    defaults: {
        track: null
    },
    
    /**
     * Draw FeatureTrack tile.
     * @param result result from server
     * @param cxt canvas context to draw on
     * @param mode mode to draw in
     * @param resolution view resolution
     * @param region region to draw
     * @param w_scale pixels per base
     * @param ref_seq reference sequence data
     */
    draw_tile: function(result, ctx, mode, resolution, region, w_scale, ref_seq) {
        var track = this,
            canvas = ctx.canvas,
            tile_low = region.get('start'),
            tile_high = region.get('end'),
            min_height = 25,
            left_offset = this.left_offset;
        
        // Drawing the summary tree (feature coverage histogram)
        if (mode === "summary_tree" || mode === "Histogram") {
            // Get summary tree data if necessary and set max if there is one.
            if (result.dataset_type !== "summary_tree") {
                var st_data = this.get_summary_tree_data(result.data, tile_low, tile_high, 200);
                if (result.max) {
                    st_data.max = result.max;
                }
                result = st_data;
            }
            // Paint summary tree into canvas
            var painter = new painters.SummaryTreePainter(result, tile_low, tile_high, this.prefs);
            painter.draw(ctx, canvas.width, canvas.height, w_scale);
            return new SummaryTreeTile(track, tile_index, resolution, canvas, result.data, result.max);
        }

        // Handle row-by-row tracks

        // Preprocessing: filter features and determine whether all unfiltered features have been slotted.
        var 
            filtered = [],
            slots = this.slotters[w_scale].slots;
            all_slotted = true;
        if ( result.data ) {
            var filters = this.filters_manager.filters;
            for (var i = 0, len = result.data.length; i < len; i++) {
                var feature = result.data[i];
                var hide_feature = false;
                var filter;
                for (var f = 0, flen = filters.length; f < flen; f++) {
                    filter = filters[f];
                    filter.update_attrs(feature);
                    if (!filter.keep(feature)) {
                        hide_feature = true;
                        break;
                    }
                }
                if (!hide_feature) {
                    // Feature visible.
                    filtered.push(feature);
                    // Set flag if not slotted.
                    if ( !(feature[0] in slots) ) {
                        all_slotted = false;
                    }
                }
            }
        }        
        
        // Create painter.
        var filter_alpha_scaler = (this.filters_manager.alpha_filter ? new FilterScaler(this.filters_manager.alpha_filter) : null);
        var filter_height_scaler = (this.filters_manager.height_filter ? new FilterScaler(this.filters_manager.height_filter) : null);
        // HACK: ref_seq will only be defined for ReadTracks, and only the ReadPainter accepts that argument
        var painter = new (this.painter)(filtered, tile_low, tile_high, this.prefs, mode, filter_alpha_scaler, filter_height_scaler, ref_seq);
        var feature_mapper = null;

        // console.log(( tile_low - this.view.low ) * w_scale, tile_index, w_scale);
        ctx.fillStyle = this.prefs.block_color;
        ctx.font = ctx.canvas.manager.default_font;
        ctx.textAlign = "right";
        
        if (result.data) {
            // Draw features.
            feature_mapper = painter.draw(ctx, canvas.width, canvas.height, w_scale, slots);
            feature_mapper.translation = -left_offset;
        }
        
        return new FeatureTrackTile(track, tile_index, resolution, canvas, result.data, w_scale, mode, result.message, all_slotted, feature_mapper);        
    }
});

/**
 * --- Views ---
 */

var TileView = Backbone.View.extend({
    
});

var ToolParameterTreeView = Backbone.View.extend({
    className: 'tool-parameter-tree',
    
    initialize: function(options) {
        this.model = options.model;  
    },
    
    render: function() {
        var width = 960,
            height = 2000;

        // Layout tree.
        var cluster = d3.layout.cluster()
            .size([height, width - 160]);

        var diagonal = d3.svg.diagonal()
            .projection(function(d) { return [d.y, d.x]; });

        // Set up vis element.
        var vis = d3.select(this.$el[0])
          .append("svg")
            .attr("width", width)
            .attr("height", height)
          .append("g")
            .attr("transform", "translate(80, 0)");

        // Set up nodes, links.
        var nodes = cluster.nodes(this.model.get('tree_data'));

        var link = vis.selectAll("path.link")
          .data(cluster.links(nodes))
        .enter().append("path")
          .attr("class", "link")
          .attr("d", diagonal);

        var node = vis.selectAll("g.node")
          .data(nodes)
        .enter().append("g")
          .attr("class", "node")
          .attr("transform", function(d) { return "translate(" + d.y + "," + d.x + ")"; });
  
        node.on("click", function(d, i) {
            console.log(d, i);  
        });

        node.append("circle")
          .attr("r", 4.5);

        node.append("text")
          .attr("dx", function(d) { return d.children ? -8 : 8; })
          .attr("dy", 3)
          .attr("text-anchor", function(d) { return d.children ? "end" : "start"; })
          .text(function(d) { return d.name; });
    }
});