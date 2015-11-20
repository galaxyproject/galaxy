/**
 * Visualization and components for Sweepster, a visualization for exploring a tool's parameter space via
 * genomic visualization.
 */

define([
    "libs/underscore",
    "libs/d3",
    "viz/trackster/util",
    "viz/visualization",
    "viz/trackster/tracks",
    "mvc/tool/tools",
    "mvc/dataset/data",
    "utils/config",
    "mvc/ui/icon-button"

], function(_, d3, util, visualization, tracks, tools, data, config, mod_icon_btn) {

/**
 * A collection of tool input settings. Object is useful for keeping a list of settings
 * for future use without changing the input's value and for preserving inputs order.
 */
var ToolInputsSettings = Backbone.Model.extend({
    defaults: {
        inputs: null,
        values: null
    }
});

/**
 * Tree for a tool's parameters.
 */
var ToolParameterTree = Backbone.Model.extend({
    defaults: {
        tool: null,
        tree_data: null
    },

    initialize: function(options) {
        // Set up tool parameters to work with tree.
        var self = this;
        this.get('tool').get('inputs').each(function(input) {
            // Listen for changes to input's attributes.
            input.on('change:min change:max change:num_samples', function(input) {
                if (input.get('in_ptree')) {
                    self.set_tree_data();
                }
            }, self);
            input.on('change:in_ptree', function(input) {
                if (input.get('in_ptree')) {
                    self.add_param(input);
                }
                else {
                    self.remove_param(input);
                }
                self.set_tree_data();
            }, self);
        });

        // If there is a config, use it.
        if (options.config) {
            _.each(options.config, function(input_config) {
                var input = self.get('tool').get('inputs').find(function(input) {
                    return input.get('name') === input_config.name;
                });
                self.add_param(input);
                input.set(input_config);
            });
        }
    },

    add_param: function(param) {
        // If parameter already present, do not add it.
        if (param.get('ptree_index')) { return; }

        param.set('in_ptree', true);
        param.set('ptree_index', this.get_tree_params().length);
    },

    remove_param: function(param) {
        // Remove param from tree.
        param.set('in_ptree', false);
        param.set('ptree_index', null);

        // Update ptree indices for remaining params.
        _(this.get_tree_params()).each(function(input, index) {
            // +1 to use 1-based indexing.
            input.set('ptree_index', index + 1);
        });
    },

    /**
     * Sets tree data using tool's inputs.
     */
    set_tree_data: function() {
        // Get samples for each parameter.
        var params_samples = _.map(this.get_tree_params(), function(param) {
                return {
                    param: param,
                    samples: param.get_samples()
                };
            });
        var node_id = 0,
            // Creates tree data recursively.
            create_tree_data = function(params_samples, index) {
                var param_samples = params_samples[index],
                    param = param_samples.param,
                    param_label = param.get('label'),
                    settings = param_samples.samples;

                // Create leaves when last parameter setting is reached.
                if (params_samples.length - 1 === index) {
                    return _.map(settings, function(setting) {
                        return {
                            id: node_id++,
                            name: setting,
                            param: param,
                            value: setting
                        };
                    });
                }

                // Recurse to handle other parameters.
                return _.map(settings, function(setting) {
                    return {
                        id: node_id++,
                        name: setting,
                        param: param,
                        value: setting,
                        children: create_tree_data(params_samples, index + 1)
                    };
                });
            };

        this.set('tree_data', {
            name: 'Root',
            id: node_id++,
            children: (params_samples.length !== 0 ? create_tree_data(params_samples, 0) : null)
        });
    },

    get_tree_params: function() {
        // Filter and sort parameters to get list in tree.
        return _(this.get('tool').get('inputs').where( {in_ptree: true} ))
                 .sortBy( function(input) { return input.get('ptree_index'); } );
    },

    /**
     * Returns number of leaves in tree.
     */
    get_num_leaves: function() {
        return this.get_tree_params().reduce(function(memo, param) { return memo * param.get_samples().length; }, 1);
    },

    /**
     * Returns array of ToolInputsSettings objects based on a node and its subtree.
     */
    get_node_settings: function(target_node) {
        // -- Get fixed settings from tool and parent nodes.

        // Start with tool's settings.
        var fixed_settings = this.get('tool').get_inputs_dict();

        // Get fixed settings using node's parents.
        var cur_node = target_node.parent;
        if (cur_node) {
            while(cur_node.depth !== 0) {
                fixed_settings[cur_node.param.get('name')] = cur_node.value;
                cur_node = cur_node.parent;
            }
        }

        // Walk subtree starting at clicked node to get full list of settings.
        var self = this,
            get_settings = function(node, settings) {
                // Add setting for this node. Root node does not have a param,
                // however.
                if (node.param) {
                    settings[node.param.get('name')] = node.value;
                }

                if (!node.children) {
                    // At leaf node, so return settings.
                    return new ToolInputsSettings({
                        inputs: self.get('tool').get('inputs'),
                        values: settings
                    });
                }
                else {
                    // At interior node: return list of subtree settings.
                    return _.flatten( _.map(node.children, function(c) { return get_settings(c, _.clone(settings)); }) );
                }
            },
            all_settings = get_settings(target_node, fixed_settings);

        // If user clicked on leaf, settings is a single dict. Convert to array for simplicity.
        if (!_.isArray(all_settings)) { all_settings = [ all_settings ]; }

        return all_settings;
    },

    /**
     * Returns all nodes connected a particular node; this includes parents and children of the node.
     */
    get_connected_nodes: function(node) {
        var get_subtree_nodes = function(a_node) {
            if (!a_node.children) {
                return a_node;
            }
            else {
                // At interior node: return subtree nodes.
                return _.flatten( [a_node, _.map(a_node.children, function(c) { return get_subtree_nodes(c); })] );
            }
        };

        // Get node's parents.
        var parents = [],
            cur_parent = node.parent;
        while(cur_parent) {
            parents.push(cur_parent);
            cur_parent = cur_parent.parent;
        }

        return _.flatten([parents, get_subtree_nodes(node)]);
    },

    /**
     * Returns the leaf that corresponds to a settings collection.
     */
    get_leaf: function(settings) {
        var cur_node = this.get('tree_data'),
            find_child = function(children) {
                return _.find(children, function(child) {
                    return settings[child.param.get('name')] === child.value;
                });
            };

        while (cur_node.children) {
            cur_node = find_child(cur_node.children);
        }
        return cur_node;
    },

    /**
     * Returns a list of parameters used in tree.
     */
    toJSON: function() {
        // FIXME: returning and jsonifying complete param causes trouble on the server side,
        // so just use essential attributes for now.
        return this.get_tree_params().map(function(param) {
            return {
                name: param.get('name'),
                min: param.get('min'),
                max: param.get('max'),
                num_samples: param.get('num_samples')
            };
        });
    }
});

var SweepsterTrack = Backbone.Model.extend({
    defaults: {
        track: null,
        mode: 'Pack',
        settings: null,
        regions: null
    },

    initialize: function(options) {
        this.set('regions', options.regions);
        if (options.track) {
            // FIXME: find a better way to deal with needed URLs:
            var track_config = _.extend({
                                    data_url: Galaxy.root + 'dummy1',
                                    converted_datasets_state_url: Galaxy.root + 'dummy2'
                                }, options.track);
            this.set('track', tracks.object_from_template(track_config, {}, null));
        }
    },

    same_settings: function(a_track) {
        var this_settings = this.get('settings'),
            other_settings = a_track.get('settings');
        for (var prop in this_settings) {
            if (!other_settings[prop] ||
                this_settings[prop] !== other_settings[prop]) {
                return false;
            }
        }
        return true;
    },

    toJSON: function() {
        return {
            track: this.get('track').to_dict(),
            settings: this.get('settings'),
            regions: this.get('regions')
        };
    }
});

var TrackCollection = Backbone.Collection.extend({
    model: SweepsterTrack
});

/**
 * Sweepster visualization model.
 */
var SweepsterVisualization = visualization.Visualization.extend({
    defaults: _.extend({}, visualization.Visualization.prototype.defaults, {
        dataset: null,
        tool: null,
        parameter_tree: null,
        regions: null,
        tracks: null,
        default_mode: 'Pack'
    }),

    initialize: function(options) {
        this.set('dataset', new data.Dataset(options.dataset));
        this.set('tool', new tools.Tool(options.tool));
        this.set('regions', new visualization.GenomeRegionCollection(options.regions));
        this.set('tracks', new TrackCollection(options.tracks));

        var tool_with_samplable_inputs = this.get('tool');
        this.set('tool_with_samplable_inputs', tool_with_samplable_inputs);
        // Remove complex parameters for now.
        tool_with_samplable_inputs.remove_inputs( [ 'data', 'hidden_data', 'conditional', 'text' ] );

        this.set('parameter_tree', new ToolParameterTree({
            tool: tool_with_samplable_inputs,
            config: options.tree_config
        }));
    },

    add_track: function(track) {
        this.get('tracks').add(track);
    },

    toJSON: function() {
        return {
            id: this.get('id'),
            title: 'Parameter exploration for dataset \''  + this.get('dataset').get('name') + '\'',
            type: 'sweepster',
            dataset_id: this.get('dataset').id,
            tool_id: this.get('tool').id,
            regions: this.get('regions').toJSON(),
            tree_config: this.get('parameter_tree').toJSON(),
            tracks: this.get('tracks').toJSON()
        };
    }
});

/**
 * --- Views ---
 */

/**
 * Sweepster track view.
 */
var SweepsterTrackView = Backbone.View.extend({
    tagName: 'tr',

    TILE_LEN: 250,

    initialize: function(options) {
        this.canvas_manager = options.canvas_manager;
        this.render();
        this.model.on('change:track change:mode', this.draw_tiles, this);
    },

    render: function() {
        // Render settings icon and popup.
        // TODO: use template.
        var settings = this.model.get('settings'),
            values = settings.get('values'),
            settings_td = $('<td/>').addClass('settings').appendTo(this.$el),
            settings_div = $('<div/>').addClass('track-info').hide().appendTo(settings_td);
        settings_div.append( $('<div/>').css('font-weight', 'bold').text('Track Settings') );
        settings.get('inputs').each(function(input) {
            settings_div.append( input.get('label') + ': ' + values[input.get('name')] + '<br/>');
        });
        var self = this,
            run_on_dataset_button = $('<button/>').appendTo(settings_div).text('Run on complete dataset').click(function() {
                settings_div.toggle();
                self.trigger('run_on_dataset', settings);
            });
        var icon_menu = mod_icon_btn.create_icon_buttons_menu([
            {
                title: 'Settings',
                icon_class: 'gear track-settings',
                on_click: function() {
                    settings_div.toggle();
                }
            },
            {
                title: 'Remove',
                icon_class: 'cross-circle',
                on_click: function() {
                    self.$el.remove();
                    $('.tooltip').remove();
                    // TODO: remove track from viz collection.
                }
            }
        ]);
        settings_td.prepend(icon_menu.$el);

        // Render tile placeholders.
        this.model.get('regions').each(function() {
            self.$el.append($('<td/>').addClass('tile').html(
                $('<img/>').attr('src', Galaxy.root + 'images/loading_large_white_bg.gif')
            ));
        });

        if (this.model.get('track')) {
            this.draw_tiles();
        }
    },

    /**
     * Draw tiles for regions.
     */
    draw_tiles: function() {
        var self = this,
            track = this.model.get('track'),
            regions = this.model.get('regions'),
            tile_containers = this.$el.find('td.tile');

        // Do nothing if track is not defined.
        if (!track) { return; }

        // When data is ready, draw tiles.
        $.when(track.data_manager.data_is_ready()).then(function(data_ok) {
            // Draw tile for each region.
            regions.each(function(region, index) {
                var resolution = region.length() / self.TILE_LEN,
                    w_scale = 1/resolution,
                    mode = self.model.get('mode');
                $.when(track.data_manager.get_data(region, mode, resolution, {})).then(function(tile_data) {
                    var canvas = self.canvas_manager.new_canvas();
                    canvas.width = self.TILE_LEN;
                    canvas.height = track.get_canvas_height(tile_data, mode, w_scale, canvas.width);
                    track.draw_tile(tile_data, canvas.getContext('2d'), mode, region, w_scale);
                    $(tile_containers[index]).empty().append(canvas);
                });
            });
        });
    }
});

/**
 * Tool input (parameter) that enables both value and sweeping inputs. View is unusual as
 * it augments an existing input form row rather than creates a completely new HTML element.
 */
var ToolInputValOrSweepView = Backbone.View.extend({

    // Template for rendering sweep inputs:
    number_input_template: '<div class="form-row-input sweep">' +
                           '<input class="min" type="text" size="6" value="<%= min %>"> - ' +
                           '<input class="max" type="text" size="6" value="<%= max %>">' +
                           ' samples: <input class="num_samples" type="text" size="1" value="<%= num_samples %>">' +
                           '</div>',

    select_input_template: '<div class="form-row-input sweep"><%= options %></div>',

    initialize: function(options) {
        this.$el = options.tool_row;
        this.render();
    },

    render: function() {
        var input = this.model,
            type = input.get('type'),
            single_input_row = this.$el.find('.form-row-input'),
            sweep_inputs_row = null;

        // Update tool inputs as single input changes.
        single_input_row.find(':input').change(function() {
            input.set('value', $(this).val());
        });

        // Add row for parameter sweep inputs.
        if (input instanceof tools.IntegerToolParameter) {
            sweep_inputs_row = $( _.template(this.number_input_template)(this.model.toJSON()) );
        }
        else if (input instanceof tools.SelectToolParameter) {
            var options = _.map(this.$el.find('select option'), function(option) {
                    return $(option).val();
                }),
                options_text = options.join(', ');
            sweep_inputs_row = $( _.template(this.select_input_template)({
                options: options_text
            }) );
        }
        sweep_inputs_row.insertAfter(single_input_row);

        // Add buttons for adding/removing parameter.
        var self = this,
            menu = mod_icon_btn.create_icon_buttons_menu([
            {
                title: 'Add parameter to tree',
                icon_class: 'plus-button',
                on_click: function () {
                    input.set('in_ptree', true);
                    single_input_row.hide();
                    sweep_inputs_row.show();
                    $(this).hide();
                    self.$el.find('.icon-button.toggle').show();
                }

            },
            {
                title: 'Remove parameter from tree',
                icon_class: 'toggle',
                on_click: function() {
                    // Remove parameter from tree params where name matches clicked paramter.
                    input.set('in_ptree', false);
                    sweep_inputs_row.hide();
                    single_input_row.show();
                    $(this).hide();
                    self.$el.find('.icon-button.plus-button').show();
                }
            }
            ],
            {

            });
            this.$el.prepend(menu.$el);

        // Show/hide input rows and icons depending on whether parameter is in the tree.
        if (input.get('in_ptree')) {
            single_input_row.hide();
            self.$el.find('.icon-button.plus-button').hide();
        }
        else {
            self.$el.find('.icon-button.toggle').hide();
            sweep_inputs_row.hide();
        }

        // Update input's min, max, number of samples as values change.
        _.each(['min', 'max', 'num_samples'], function(attr) {
            sweep_inputs_row.find('.' + attr).change(function() {
                input.set(attr, parseFloat( $(this).val() ));
            });
        });
    }
});

var ToolParameterTreeDesignView = Backbone.View.extend({
    className: 'tree-design',

    initialize: function(options) {
        this.render();
    },

    render: function() {
        // Start with tool form view.
        var tool_form_view = new tools.ToolFormView({
            model: this.model.get('tool')
        });
        tool_form_view.render();
        this.$el.append(tool_form_view.$el);

        // Set up views for each tool input.
        var self = this,
            inputs = self.model.get('tool').get('inputs');
        this.$el.find('.form-row').not('.form-actions').each(function(i) {
            var input_view = new ToolInputValOrSweepView({
                model: inputs.at(i),
                tool_row: $(this)
            });
        });
    }
});

/**
 * Displays and updates parameter tree.
 */
var ToolParameterTreeView = Backbone.View.extend({
    className: 'tool-parameter-tree',

    initialize: function(options) {
        // When tree data changes, re-render.
        this.model.on('change:tree_data', this.render, this);
    },

    render: function() {
        // Start fresh.
        this.$el.children().remove();

        var tree_params = this.model.get_tree_params();
        if (!tree_params.length) {
            return;
        }

        // Set width, height based on params and samples.
        this.width = 100 * (2 + tree_params.length);
        this.height = 15 * this.model.get_num_leaves();

        var self = this;

        // Layout tree.
        var cluster = d3.layout.cluster()
            .size([this.height, this.width - 160]);

        var diagonal = d3.svg.diagonal()
            .projection(function(d) { return [d.y, d.x]; });

        // Layout nodes.
        var nodes = cluster.nodes(this.model.get('tree_data'));

        // Setup and add labels for tree levels.
        var param_depths = _.uniq(_.pluck(nodes, "y"));
        _.each(tree_params, function(param, index) {
            var x = param_depths[index+1],
                center_left = $('#center').position().left;
            self.$el.append( $('<div>').addClass('label')
                                       .text(param.get('label'))
                                       .css('left', x + center_left) );
        });

        // Set up vis element.
        var vis = d3.select(this.$el[0])
          .append("svg")
            .attr("width", this.width)
            .attr("height", this.height + 30)
          .append("g")
            .attr("transform", "translate(40, 20)");

        // Draw links.
        var link = vis.selectAll("path.link")
          .data(cluster.links(nodes))
        .enter().append("path")
          .attr("class", "link")
          .attr("d", diagonal);

        // Draw nodes.
        var node = vis.selectAll("g.node")
          .data(nodes)
        .enter().append("g")
          .attr("class", "node")
          .attr("transform", function(d) { return "translate(" + d.y + "," + d.x + ")"; })
          .on('mouseover', function(a_node) {
            var connected_node_ids = _.pluck(self.model.get_connected_nodes(a_node), 'id');
            // TODO: probably can use enter() to do this more easily.
            node.filter(function(d) {
                return _.find(connected_node_ids, function(id) { return id === d.id; }) !== undefined;
            }).style('fill', '#f00');
          })
          .on('mouseout', function() {
            node.style('fill', '#000');
          });

        node.append("circle")
          .attr("r", 9);

        node.append("text")
          .attr("dx", function(d) { return d.children ? -12 : 12; })
          .attr("dy", 3)
          .attr("text-anchor", function(d) { return d.children ? "end" : "start"; })
          .text(function(d) { return d.name; });
    }
});

/**
 * Sweepster visualization view. View requires rendering in 3-panel setup for now.
 */
var SweepsterVisualizationView = Backbone.View.extend({
    className: 'Sweepster',

    helpText:
        '<div><h4>Getting Started</h4>' +
        '<ol><li>Create a parameter tree by using the icons next to the tool\'s parameter names to add or remove parameters.' +
        '<li>Adjust the tree by using parameter inputs to select min, max, and number of samples' +
        '<li>Run the tool with different settings by clicking on tree nodes' +
        '</ol></div>',

    initialize: function(options) {
        this.canvas_manager = new visualization.CanvasManager(this.$el.parents('body'));
        this.tool_param_tree_view = new ToolParameterTreeView({ model: this.model.get('parameter_tree') });
        this.track_collection_container = $('<table/>').addClass('tracks');

        // Handle node clicks for tree data.
        this.model.get('parameter_tree').on('change:tree_data', this.handle_node_clicks, this);

        // Each track must have a view so it has a canvas manager.
        var self = this;
        this.model.get('tracks').each(function(track) {
            track.get('track').view = self;
        });

        // Set block, reverse strand block colors; these colors will be used for all tracks.
        this.config = config.ConfigSettingCollection.from_models_and_saved_values(
            [
                { key: 'name', label: 'Name', type: 'text', default_value: '' },
                { key: 'a_color', label: 'A Color', type: 'color', default_value: "#FF0000" },
                { key: 'c_color', label: 'C Color', type: 'color', default_value: "#00FF00" },
                { key: 'g_color', label: 'G Color', type: 'color', default_value: "#0000FF" },
                { key: 't_color', label: 'T Color', type: 'color', default_value: "#FF00FF" },
                { key: 'n_color', label: 'N Color', type: 'color', default_value: "#AAAAAA" },
                { key: 'block_color', label: 'Block color', type: 'color' },
                { key: 'reverse_strand_color', label: 'Antisense strand color', type: 'color' },
            ], {}
        );
    },

    render: function() {
        // Render tree design view in left panel.
        var tree_design_view = new ToolParameterTreeDesignView({
            model: this.model.get('parameter_tree')
        });

        $('#left').append(tree_design_view.$el);

        // Render track collection container/view in right panel.
        var self = this,
            regions = self.model.get('regions'),
            tr = $('<tr/>').appendTo(this.track_collection_container);

        regions.each(function(region) {
            tr.append( $('<th>').text(region.toString()) );
        });
        tr.children().first().attr('colspan', 2);

        var tracks_div = $('<div>').addClass('tiles');
        $('#right').append( tracks_div.append(this.track_collection_container) );

        self.model.get('tracks').each(function(track) {
            self.add_track(track);
        });

        // -- Render help and tool parameter tree in center panel. --

        // Help includes text and a close button.
        var help_div = $(this.helpText).addClass('help'),
            close_button = mod_icon_btn.create_icon_buttons_menu([
            {
                title: 'Close',
                icon_class: 'cross-circle',
                on_click: function() {
                    $('.tooltip').remove();
                    help_div.remove();
                }
            }
            ]);

        help_div.prepend(close_button.$el.css('float', 'right'));
        $('#center').append(help_div);

        // Parameter tree:
        this.tool_param_tree_view.render();
        $('#center').append(this.tool_param_tree_view.$el);

        // Set up handler for tree node clicks.
        this.handle_node_clicks();

        // Set up visualization menu.
        var menu = mod_icon_btn.create_icon_buttons_menu(
            [
                // Save.
                /*
                { icon_class: 'disk--arrow', title: 'Save', on_click: function() {
                    // Show saving dialog box
                    show_modal("Saving...", "progress");

                    viz.save().success(function(vis_info) {
                        hide_modal();
                        viz.set({
                            'id': vis_info.vis_id,
                            'has_changes': false
                        });
                    })
                    .error(function() {
                        show_modal( "Could Not Save", "Could not save visualization. Please try again later.",
                                    { "Close" : hide_modal } );
                    });
                } },
                */
                // Change track modes.
                {
                    icon_class: 'chevron-expand',
                    title: 'Set display mode'
                },
                // Close viz.
                {
                    icon_class: 'cross-circle',
                    title: 'Close',
                    on_click: function() {
                        window.location = "${h.url_for( controller='visualization', action='list' )}";
                    }
                }
            ],
            {
                tooltip_config: {placement: 'bottom'}
            });

            // Create mode selection popup. Mode selection changes default mode and mode for all tracks.
            var modes = ['Squish', 'Pack'],
                mode_mapping = {};
            _.each(modes, function(mode) {
                mode_mapping[mode] = function() {
                    self.model.set('default_mode', mode);
                    self.model.get('tracks').each(function(track) {
                        track.set('mode', mode);
                    });
                };
            });

            make_popupmenu(menu.$el.find('.chevron-expand'), mode_mapping);

        menu.$el.attr("style", "float: right");
        $("#right .unified-panel-header-inner").append(menu.$el);
    },

    get_base_color: function(base) {
        return this.config.get_value(base.toLowerCase() + '_color') ||
               this.config.get_value('n_color');
    },

    run_tool_on_dataset: function(settings) {
        var tool = this.model.get('tool'),
            tool_name = tool.get('name'),
            dataset = this.model.get('dataset');
        tool.set_input_values(settings.get('values'));
        $.when(tool.rerun(dataset)).then(function(outputs) {
            // TODO.
        });

        show_modal('Running ' + tool_name + ' on complete dataset',
                       tool_name + ' is running on dataset \'' +
                       dataset.get('name') + '\'. Outputs are in the dataset\'s history.',
                       {
                        'Ok': function() { hide_modal(); }
                       });
    },

    /**
     * Add track to model and view.
     */
    add_track: function(pm_track) {
        var self = this,
            param_tree = this.model.get('parameter_tree');

        // Add track to model.
        self.model.add_track(pm_track);

        var track_view = new SweepsterTrackView({
            model: pm_track,
            canvas_manager: self.canvas_manager
        });
        track_view.on('run_on_dataset', self.run_tool_on_dataset, self);
        self.track_collection_container.append(track_view.$el);
        track_view.$el.hover(function() {
            var settings_leaf = param_tree.get_leaf(pm_track.get('settings').get('values'));
            var connected_node_ids = _.pluck(param_tree.get_connected_nodes(settings_leaf), 'id');

            // TODO: can do faster with enter?
            d3.select(self.tool_param_tree_view.$el[0]).selectAll("g.node")
            .filter(function(d) {
                return _.find(connected_node_ids, function(id) { return id === d.id; }) !== undefined;
            }).style('fill', '#f00');
        },
        function() {
            d3.select(self.tool_param_tree_view.$el[0]).selectAll("g.node").style('fill', '#000');
        });
        return pm_track;
    },

    /**
     * Sets up handling when tree nodes are clicked. When a node is clicked, the tool is run for each of
     * the settings defined by the node's subtree and tracks are added for each run.
     */
    handle_node_clicks: function() {
        // When node clicked in tree, run tool and add tracks to model.
        var self = this,
            param_tree = this.model.get('parameter_tree'),
            regions = this.model.get('regions'),
            node = d3.select(this.tool_param_tree_view.$el[0]).selectAll("g.node");
        node.on("click", function(d, i) {
            // Get all settings corresponding to node.
            var tool = self.model.get('tool'),
                dataset = self.model.get('dataset'),
                all_settings = param_tree.get_node_settings(d),
                run_jobs_deferred = $.Deferred();

            // Do not allow 10+ jobs to be run.
            if (all_settings.length >= 10) {
                show_modal("Whoa there cowboy!",
                            "You clicked on a node to try " + self.model.get('tool').get('name') +
                            " with " + all_settings.length +
                            " different combinations of settings. You can only run 10 jobs at a time.",
                            {
                                "Ok": function() { hide_modal(); run_jobs_deferred.resolve(false); }
                            });
            }
            else {
                run_jobs_deferred.resolve(true);
            }

            // Take action when deferred resolves.
            $.when(run_jobs_deferred).then(function(run_jobs) {
                if (!run_jobs) { return; }

                // Create and add tracks for each settings group.
                var new_tracks = _.map(all_settings, function(settings) {
                    var pm_track = new SweepsterTrack({
                        settings: settings,
                        regions: regions,
                        mode: self.model.get('default_mode')
                    });
                    self.add_track(pm_track);
                    return pm_track;
                });

                // For each track, run tool using track's settings and update track.
                _.each(new_tracks, function(pm_track, index) {
                    setTimeout(function() {
                        // Set inputs and run tool.
                        tool.set_input_values(pm_track.get('settings').get('values'));
                        $.when(tool.rerun(dataset, regions)).then(function(output) {
                            // HACKish: output is an HDA with track config attribute. To create a track
                            // that works correctly with Backbone relational, it is necessary to
                            // use a modified version of the track config.
                            var dataset = output.first(),
                                track_config = dataset.get('track_config');
                            // Set dataset to be the tool's output.
                            track_config.dataset = dataset;
                            // Set tool to null so that it is not unpacked; unpacking it messes with
                            // the tool parameters and parameter tree.
                            track_config.tool = null;

                            track_config.prefs = self.config.to_key_value_dict();

                            // Create and add track for output dataset.
                            var track_obj = tracks.object_from_template(track_config, self, null);
                            track_obj.init_for_tool_data();

                            pm_track.set('track', track_obj);
                        });
                    }, index * 10000);
                });
            });
        });
    }
});

return {
    SweepsterVisualization: SweepsterVisualization,
    SweepsterVisualizationView: SweepsterVisualizationView
};

});
