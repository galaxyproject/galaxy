// dependencies
define(['mvc/ui/ui-portlet', 'plugin/library/ui', 'utils/utils'],
        function(Portlet, Ui, Utils) {

// widget
return Backbone.View.extend(
{
    // initialize
    initialize: function(app, options)
    {
        // link app
        this.app = app;
        
        // link chart
        this.chart = this.app.chart;
        
        // link options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // create element
        this.setElement($(this._template()));
        
        // create svg element
        this._create_svg();
        
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

    // create
    _create_svg: function() {
        // clear svg
        if (this.svg) {
            this.svg.remove();
        }
        
        // create
        this.$el.append($(this._template_svg()));
        
        // find svg element
        this.svg_el = this.$el.find('svg');
        this.svg = d3.select(this.svg_el[0]);
    },

    // add
    _draw: function(chart) {
        // link this
        var self = this;
        
        // create svg element
        this._create_svg();
            
        // set chart state
        chart.state('wait', 'Please wait...');
        
        // register process
        var process_id = chart.deferred.register();

        // identify chart type
        var chart_type = chart.get('type');
        var chart_settings = this.app.types.get(chart_type);
        
        // clean up data if there is any from previous jobs
        if (!chart_settings.execute ||
            (chart_settings.execute && chart.get('modified'))) {
            // reset jobs
            this.app.jobs.cleanup(chart);
            
            // reset modified flag
            chart.set('modified', false);
        }
        
        // create chart view
        var self = this;
        require(['plugin/charts/' + chart_type + '/' + chart_type], function(ChartView) {
            // create chart
            var view = new ChartView(self.app, {svg : self.svg});
            
            // request data
            if (chart_settings.execute) {
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
    
        // get chart settings
        var chart_settings  = this.app.types.get(chart.get('type'));
       
        // configure request
        var request_string = '';
        
        // add groups to data request
        var group_index = 0;
        chart.groups.each(function(group) {
            for (var key in chart_settings.columns) {
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
    
        // get chart settings
        var chart_settings  = this.app.types.get(chart.get('type'));
       
        // configure request
        var request_dictionary = {
            groups : []
        };
        
        // update request dataset id
        if (chart_settings.execute) {
            request_dictionary.id = chart.get('dataset_id_job');
        } else {
            request_dictionary.id = chart.get('dataset_id');
        }
        
        // add groups to data request
        var group_index = 0;
        chart.groups.each(function(group) {

            // add columns
            var columns = {};
            for (var key in chart_settings.columns) {
                columns[key] = group.get(key);
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
        return  '<div style="height: 100%; min-height: 50px;">' +
                    '<div id="info" style="position: absolute; margin-left: 10px; margin-top: 10px; margin-bottom: 50px;">' +
                        '<span id="icon" style="font-size: 1.2em; display: inline-block;"/>' +
                        '<span id="text" style="position: relative; margin-left: 5px; top: -1px; font-size: 1.0em;"/>' +
                    '</div>' +
                '</div>';
    },
    
    // template svg element
    _template_svg: function() {
        return '<svg style="height: calc(100% - 80px)"/>';
    },
    
});

});