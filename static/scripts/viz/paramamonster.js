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
                param_label = param.get('label'),
                settings = param_samples.get('samples');

            // Create leaves when last parameter setting is reached.
            if (params_samples.length - 1 === index) {
                return _.map(settings, function(setting) {
                    return {
                        name: param_label + '=' + setting,
                        param: param,
                        value: setting
                    }
                });
            }
            
            // Recurse to handle other parameters.
            return _.map(settings, function(setting) {
                 return {
                     name: param_label + '=' + setting,
                     param: param,
                     value: setting,
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
 * ParamaMonster visualization model.
 */
var ParamaMonsterVisualization = Visualization.extend({
    defaults: _.extend({}, Visualization.prototype.defaults, {
        tool: null,
        parameter_tree: null,
        regions: null
    }),
    
    initialize: function(options) {
        this.set('parameter_tree', new ToolParameterTree({ tool: this.get('tool') }));
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
  
        node.append("circle")
          .attr("r", 4.5);

        node.append("text")
          .attr("dx", function(d) { return d.children ? -8 : 8; })
          .attr("dy", 3)
          .attr("text-anchor", function(d) { return d.children ? "end" : "start"; })
          .text(function(d) { return d.name; });
    }
});

var ParamaMonsterVisualizationView = Backbone.View.extend({
    className: 'paramamonster',
    
    initialize: function(options) {
        
    },
    
    render: function() {
        // Set up tool parameter tree.
        var tool_param_tree_view = new ToolParameterTreeView({ model: this.model.get('parameter_tree') });
        tool_param_tree_view.render();
        this.$el.append(tool_param_tree_view.$el);
        
        // When node clicked in tree, run tool and show tiles.
        var node = d3.select(tool_param_tree_view.$el[0]).selectAll("g.node")
        node.on("click", function(d, i) {
            console.log(d, i);
            
            // Gather: (a) dataset of interest; (b) region(s) of interest and (c) sets of parameters based on node clicked.
            
            // Run job by submitting parameters + dataset as job inputs; get dataset ids as result.
            
            // Create tracks for all resulting dataset ids.
            
            // Display tiles for region(s) of interest.
        });
        
    },
});