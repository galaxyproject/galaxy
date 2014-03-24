// dependencies
define(['mvc/ui/ui-portlet', 'plugin/library/ui', 'utils/utils'],
        function(Portlet, Ui, Utils) {

// widget
return Backbone.View.extend(
{
    // height
    height : 300,
    
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
        
        // events
        var self = this;
        this.chart.on('redraw', function() {
            self._draw(self.chart);
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

    // add
    _draw: function(chart) {
        // link this
        var self = this;
        
        // check
        if (!chart.ready()) {
            this.app.log('viewport:_drawChart()', 'Invalid attempt to draw chart before completion.');
            return;
        }
        
        // clear svg
        if (this.svg) {
            this.svg.remove();
        }
        
        // create
        this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        this.svg.setAttribute('height', this.height);
        this.$el.append(this.svg);
        
        // find svg element
        this.svg = d3.select(this.$el.find('svg')[0]);
         
        // clear all previous handlers (including redraw listeners)
        chart.off('change:state');
        
        // link status handler
        chart.on('change:state', function() {
            // get info element
            var $info = self.$el.find('#info');
            
            // get icon
            var $icon = $info.find('#icon');
            
            // remove icon
            $icon.removeClass();
        
            // show info
            $info.show();
            $info.find('#text').html(chart.get('state_info'));

            // check status
            var state = chart.get('state');
            switch (state) {
                case 'ok':
                    $info.hide();
                    break;
                case 'failed':
                    $icon.addClass('fa fa-warning');
                    break;
                default:
                    $icon.addClass('fa fa-spinner fa-spin');
                    break;
            }
        });
        
        // set chart state
        chart.state('wait', 'Please wait...');

        // identify chart type
        var chart_type = chart.get('type');
        var chart_settings = this.app.types.get(chart_type);
        
        // create chart view
        var self = this;
        require(['plugin/charts/' + chart_type + '/' + chart_type], function(ChartView) {
            // create chart
            var view = new ChartView(self.app, {svg : self.svg});
            
            // request data
            if (chart_settings.execute) {
                self.app.jobs.submit(chart, self._defaultSettingsString(chart), self._defaultRequestString(chart), function() {
                    view.draw(chart, self._defaultRequestDictionary(chart));
                });
            } else {
                view.draw(chart, self._defaultRequestDictionary(chart));
            }
        });
    },
    
    // template
    _template: function() {
        return  '<div>' +
                    '<div id="info" style="text-align: center; margin-top: 20px;">' +
                        '<span id="icon" style="font-size: 1.2em; display: inline-block;"/>' +
                        '<span id="text" style="position: relative; margin-left: 5px; top: -1px; font-size: 1.0em;"/>' +
                    '</div>' +
                '</div>';
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
            id          : chart.get('dataset_id'),
            groups      : []
        };
        
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
    }
});

});