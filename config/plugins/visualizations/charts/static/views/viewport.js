// dependencies
define(['mvc/ui/ui-portlet', 'mvc/ui/ui-misc', 'utils/utils'],
        function(Portlet, Ui, Utils) {

/**
 *  The viewport creates and manages the dom elements used by the visualization plugins to draw the chart.
 *  Additionally, this class creates default request strings and request dictionaries parsed to the visualization plugins.
 *  This is the last class of the charts core classes before handing control over to the visualization plugins.
 */
return Backbone.View.extend({

    // list of canvas elements
    container_list: [],
    canvas_list: [],
    
    // initialize
    initialize: function(app, options) {
        // link app
        this.app = app;
        
        // link chart
        this.chart = this.app.chart;
        
        // link options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // create element
        this.setElement($(this._template()));
        
        // use full screen for viewer
        this._fullscreen(this.$el, 100);
        
        // create container element
        this._createContainer('div');
        
        // events
        var self = this;
        this.chart.on('redraw', function() {
            self._draw(self.chart);
        });
        
        // link status handler
        this.chart.on('set:state', function() {
            // get info element
            var $info = self.$el.find('#info');
            var $container = self.$el.find('.charts-viewport-container');
            
            // get icon
            var $icon = $info.find('#icon');
            
            // remove icon
            $icon.removeClass();
        
            // show info
            $info.show();
            $info.find('#text').html(self.chart.get('state_info'));
            
            // check status
            var state = self.chart.get('state');
            switch (state) {
                case 'ok':
                    $info.hide();
                    $container.show();
                    break;
                case 'failed':
                    $icon.addClass('icon fa fa-warning');
                    $container.hide();
                    break;
                default:
                    $icon.addClass('icon fa fa-spinner fa-spin');
                    $container.show();
            }
        });
    },
    
    // show
    show: function() {
        this.$el.show();
    },
    
    // hide
    hide: function() {
        this.$el.hide();
    },

    // resize to fullscreen
    _fullscreen: function($el, margin) {
        // fix size
        $el.css('height', $(window).height() - margin);
        
        // catch window resize event
        $(window).resize(function () {
            $el.css('height', $(window).height()  - margin);
        });
    },
    
    // creates n canvas elements
    _createContainer: function(tag, n) {
        // check size of requested canvas elements
        n = n || 1;
    
        // clear previous canvas elements
        for (var i in this.container_list) {
            this.container_list[i].remove();
        }
        
        // reset lists
        this.container_list = [];
        this.canvas_list = [];
        
        // create requested canvas elements
        for (var i = 0; i < n; i++) {
            // create element
            var container_el = $(this._templateContainer(tag, parseInt(100 / n)));
            
            // add to view
            this.$el.append(container_el);
            
            // add to list
            this.container_list[i] = container_el;
            
            // add a separate list for canvas elements
            this.canvas_list[i] = container_el.find('.charts-viewport-canvas').attr('id');
        }
    },
    
    // add
    _draw: function(chart) {
        // link this
        var self = this;
        
        // register process
        var process_id = this.app.deferred.register();

        // identify chart type
        var chart_type = chart.get('type');
        
        // load chart settings
        this.chart_definition = chart.definition;
        
        // determine number of svg/div-elements to create
        var n_panels = 1;
        if (chart.settings.get('use_panels') === 'true') {
            n_panels = chart.groups.length;
        }
        
        // create canvas element and add to canvas list
        this._createContainer(this.chart_definition.tag, n_panels);
            
        // set chart state
        chart.state('wait', 'Please wait...');
        
        // clean up data if there is any from previous jobs
        if (!this.chart_definition.execute ||
            (this.chart_definition.execute && chart.get('modified'))) {
            
            // reset jobs
            this.app.jobs.cleanup(chart);
            
            // reset modified flag
            chart.set('modified', false);
        }
        
        // create chart view
        var self = this;
        require(['plugin/charts/' + this.app.chartPath(chart_type) + '/wrapper'], function(ChartView) {
            if (self.chart_definition.execute) {
                self.app.jobs.request(chart, self._defaultSettingsString(chart), self._defaultRequestString(chart),
                    function() {
                        var view = new ChartView(self.app, {
                            process_id          : process_id,
                            chart               : chart,
                            request_dictionary  : self._defaultRequestDictionary(chart),
                            canvas_list         : self.canvas_list
                        });
                    },
                    function() {
                        this.app.deferred.done(process_id);
                    }
                );
            } else {
                var view = new ChartView(self.app, {
                    process_id          : process_id,
                    chart               : chart,
                    request_dictionary  : self._defaultRequestDictionary(chart),
                    canvas_list         : self.canvas_list
                });
            }
        });
    },

    //
    // REQUEST STRING FUNCTIONS
    //
    // create default chart request
    _defaultRequestString: function(chart) {
    
        // configure request
        var request_string = '';
        
        // add groups to data request
        var group_index = 0;
        var self = this;
        chart.groups.each(function(group) {
            // increase group counter
            group_index++;
            
            // add selected columns to column string
            for (var key in self.chart_definition.columns) {
                request_string += key + '_' + group_index + ':' + (parseInt(group.get(key)) + 1) + ', ';
            }
        });
        
        // return
        return request_string.substring(0, request_string.length - 2);
    },
    
    // create default chart request
    _defaultSettingsString: function(chart) {
    
        // configure settings
        var settings_string = '';
        
        // add settings to settings string
        for (key in chart.settings.attributes) {
            settings_string += key + ':' + chart.settings.get(key) + ', ';
        };
        
        // return
        return settings_string.substring(0, settings_string.length - 2);
    },

    // create default chart request
    _defaultRequestDictionary: function(chart) {
    
        // configure request
        var request_dictionary = {
            groups : []
        };
        
        // update request dataset id
        if (this.chart_definition.execute) {
            request_dictionary.id = chart.get('dataset_id_job');
        } else {
            request_dictionary.id = chart.get('dataset_id');
        }
        
        // add groups to data request
        var group_index = 0;
        var self = this;
        chart.groups.each(function(group) {

            // add columns
            var columns = {};
            for (var column_key in self.chart_definition.columns) {
                // get settings for column
                var column_settings = self.chart_definition.columns[column_key];
                
                // add to columns
                columns[column_key] = Utils.merge ({
                    index : group.get(column_key)
                }, column_settings);
            }
            
            // add group data
            request_dictionary.groups.push({
                key     : (++group_index) + ':' + group.get('key'),
                columns : columns
            });
        });
        
        // return
        return request_dictionary;
    },
    
    // template
    _template: function() {
        return  '<div class="charts-viewport">' +
                    '<div id="info" class="info">' +
                        '<span id="icon" class="icon"/>' +
                        '<span id="text" class="text" />' +
                    '</div>' +
                '</div>';
    },
    
    // template svg/div element
    _templateContainer: function(tag, width) {
        return  '<div class="charts-viewport-container" style="width:' + width + '%;">' +
                    '<div id="menu"/>' +
                    '<' + tag + ' id="' + Utils.uuid() + '" class="charts-viewport-canvas">' +
                '</div>';
    }
    
});

});