/**
 * Visualization and components for ParamaMonster, a visualization for exploring a tool's parameter space via 
 * genomic visualization.
 */
 
var ToolParameterTree = Backbone.Model.extend({
    defaults: {
        tool: null,
        samples: 4
    },
    
    
    initialize: function(options) {
        //
        // -- Create tree data from tool. --
        //
        
        // Valid inputs for tree are number, select parameters.
        var tool = this.get('tool'),
            samples = this.get('samples'),
            inputs = tool.get('inputs').filter(function(input) {
                return ( ['number', 'select'].indexOf(input.get('type')) !== -1 );
            }),
            inputs_names = _.map(inputs, function(i) { return i.get('name')});
            // Sample from all valid inputs.
            sampling = _.map(inputs, function(input) {
                var type = input.get('type');
                if (type === 'number') {
                    return d3.scale.linear().domain([input.get('min'), input.get('max')]).ticks(samples);
                }
                else if (type === 'select') {
                    return _.map(input.get('options'), function(option) {
                        return option[0];
                    });
                }
            });
            
        /**
         * Returns tree data.
         */
        var create_tree_data = function(param_names, param_settings, index) {
            // Terminate when last parameter setting is reached.
            if (param_settings.length - 1 === index) {
                return _.map(param_settings[index], function(setting) {
                    return {
                        name: setting
                    }
                });
            }
            
            // Recurse to handle other parameters.
            return _.map(param_settings[index], function(setting) {
                 return {
                     name: param_names[index] + ':' + setting,
                     children: create_tree_data(param_names, param_settings, index + 1)
                 }
            });       
        };
        
        var tree_data = {
            name: 'Parameter Tree for ' + tool.get('name'),
            children: create_tree_data(inputs_names, sampling, 0)
        };
            
        // Set valid inputs, tree data for later use.
        this.set('valid_inputs', inputs);
        this.set('tree_data', tree_data);
    }
    
});

var TileView = Backbone.View.extend({
    
});

var ToolParameterTreeView = Backbone.View.extend({
    className: 'paramamonster',
    
    initialize: function(options) {
        this.model = options.model;  
    },
    
    render: function() {
        var width = 960,
            height = 2000;

        var cluster = d3.layout.cluster()
            .size([height, width - 160]);

        var diagonal = d3.svg.diagonal()
            .projection(function(d) { return [d.y, d.x]; });

        var vis = d3.select(this.$el[0])
          .append("svg")
            .attr("width", width)
            .attr("height", height)
          .append("g")
            .attr("transform", "translate(80, 0)");

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
              .attr("transform", function(d) { return "translate(" + d.y + "," + d.x + ")"; })

          node.append("circle")
              .attr("r", 4.5);

          node.append("text")
              .attr("dx", function(d) { return d.children ? -8 : 8; })
              .attr("dy", 3)
              .attr("text-anchor", function(d) { return d.children ? "end" : "start"; })
              .text(function(d) { return d.name; });
    }
});