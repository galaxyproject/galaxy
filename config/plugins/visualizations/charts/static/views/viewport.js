// dependencies
define(['mvc/ui/ui-portlet', 'plugin/library/ui', 'utils/utils'],
        function(Portlet, Ui, Utils) {

// widget
return Backbone.View.extend({
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
        this._fullscreen(this.$el, 80);
        
        // create canvas element
        this._create_canvas('div');
        
        // events
        var self = this;
        this.chart.on('redraw', function() {
            self._draw(self.chart);
        });
        
        // link status handler
        this.chart.on('set:state', function() {
            // get info element
            var $info = self.$el.find('#info');
            
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
                    break;
                case 'failed':
                    $icon.addClass('fa fa-warning');
                    break;
                default:
                    $icon.addClass('fa fa-spinner fa-spin');
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
    
    // create
    _create_canvas: function(element) {
        // clear canvas
        if (this.canvas) {
            this.canvas.remove();
        }
        
        // create
        this.$el.append($(this._template_canvas(element)));
        
        // find canvas element
        var canvas_el = this.$el.find('.canvas');
        if (element == 'svg') {
            this.canvas = d3.select(canvas_el[0]);
        } else {
            this.canvas = canvas_el;
        }
    },
    
    // add
    _draw: function(chart) {
        // link this
        var self = this;
        
        // register process
        var process_id = chart.deferred.register();

        // identify chart type
        var chart_type = chart.get('type');
        
        // load chart settings
        this.chart_settings = this.app.types.get(chart_type);
        
        // create canvas element
        this._create_canvas(this.chart_settings.element);
            
        // set chart state
        chart.state('wait', 'Please wait...');
        
        // clean up data if there is any from previous jobs
        if (!this.chart_settings.execute ||
            (this.chart_settings.execute && chart.get('modified'))) {
            // reset jobs
            this.app.jobs.cleanup(chart);
            
            // reset modified flag
            chart.set('modified', false);
        }
        
        // create chart view
        var self = this;
        require(['plugin/charts/' + chart_type + '/' + chart_type], function(ChartView) {
            // create chart
            var view = new ChartView(self.app, {canvas : self.canvas});
            
            // request data
            if (self.chart_settings.execute) {
                if (chart.get('dataset_id_job') == '') {
                    // submit job
                    self.app.jobs.submit(chart, self._defaultSettingsString(chart), self._defaultRequestString(chart),
                        function() {
                            view.draw(process_id, chart, self._defaultRequestDictionary(chart));
                        },
                        function() {
                            chart.deferred.done(process_id);
                        });
                } else {
                    // load data into view
                    view.draw(process_id, chart, self._defaultRequestDictionary(chart));
                }
            } else {
                // load data into view
                view.draw(process_id, chart, self._defaultRequestDictionary(chart));
            }
        });
    },
    
    // create default chart request
    _defaultRequestString: function(chart) {
    
        // configure request
        var request_string = '';
        
        // add groups to data request
        var group_index = 0;
        var self = this;
        chart.groups.each(function(group) {
            for (var key in self.chart_settings.columns) {
                request_string += key + '_' + (++group_index) + ':' + (parseInt(group.get(key)) + 1) + ', ';
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
        if (this.chart_settings.execute) {
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
            for (var key in self.chart_settings.columns) {
                // get settings for column
                var column_settings = self.chart_settings.columns[key];
                
                // add to columns
                columns[key] = {
                    index       : group.get(key),
                    is_label    : column_settings.is_label
                }
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
        return  '<div style="height: inherit; min-height: 50px;">' +
                    '<div id="info" style="position: absolute; margin-left: 10px; margin-top: 10px; margin-bottom: 50px;">' +
                        '<span id="icon" style="font-size: 1.2em; display: inline-block;"/>' +
                        '<span id="text" style="position: relative; margin-left: 5px; top: -1px; font-size: 1.0em;"/>' +
                    '</div>' +
                '</div>';
    },
    
    // template svg/div element
    _template_canvas: function(element) {
        return '<' + element + ' class="canvas" style="height: 100%;"/>';
    }
    
});

});