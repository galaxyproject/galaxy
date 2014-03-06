// dependencies
define(['mvc/ui/ui-portlet', 'plugin/library/ui', 'utils/utils'],
        function(Portlet, Ui, Utils) {

// widget
return Backbone.View.extend(
{
    // list
    list: {},
    
    // options
    optionsDefault :
    {
        height : 300
    },
    
    // initialize
    initialize: function(app, options)
    {
        // link app
        this.app = app;
        
        // link options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // add table to portlet
        this.portlet = new Portlet.View({
            title       : 'title',
            height      : this.options.height,
            overflow    : 'hidden',
            operations  : {
                'edit'  : new Ui.ButtonIcon({
                    icon    : 'fa-gear',
                    tooltip : 'Customize Chart',
                    title   : 'Customize'
                })
            }
        });
        
        // set this element
        this.setElement(this.portlet.$el);
        
        // events
        var self = this;
        
        // remove
        this.app.charts.on('remove', function(chart) {
            self._removeChart(chart.id);
        });
        
        // replace
        this.app.charts.on('change', function(chart) {
            if (chart.get('state') == 'redraw') {
                self._refreshChart(chart);
            }
        });
    },
    
    // show
    showChart: function(chart_id) {
        // show
        this.show();
        
        // hide all
        this.hideCharts();
        
        // identify selected item from list
        var item = this.list[chart_id];
        if (item) {
            // get chart
            var chart = self.app.charts.get(chart_id);
                
            // update portlet
            this.portlet.title(chart.get('title'));
            this.portlet.setOperation('edit', function() {
                // get chart
                self.app.chart.copy(chart);
                
                // show edit
                self.app.charts_view.hide();
                self.app.chart_view.$el.show();
            });
        
            // show selected chart
            item.$el.show();
        
            // this trigger d3 update events
            $(window).trigger('resize');
        }
    },
    
    // hide charts
    hideCharts: function() {
        this.$el.find('.item').hide();
    },
    
    // show
    show: function() {
        $('.tooltip').hide();
        this.$el.show();
    },
    
    // hide
    hide: function() {
        $('.tooltip').hide();
        this.$el.hide();
    },

    // add
    _refreshChart: function(chart) {
        // link this
        var self = this;
        
        // backup chart details
        var chart_id = chart.id;
    
        // make sure that svg does not exist already
        this._removeChart(chart_id);
            
        // create id
        var id = '#' + chart_id;
        
        // create element
        var $chart_el = $(this._template({id: id, height : this.options.height}));
        
        // add to portlet
        this.portlet.append($chart_el);
        
        // find svg element
        var svg = d3.select(id + ' svg');
        
        // add chart to list
        this.list[chart_id] = {
            svg : svg,
            $el : $chart_el
        }
        
        // show chart from list
        this.showChart(chart_id);
        
        // link status handler
        chart.on('change:state', function() {
            // get info element
            var $info = $chart_el.find('#info');
            
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
        require(['plugin/charts/' + chart_type], function(ChartView) {
            // create chart
            var view = new ChartView(self.app, {svg : svg});
            
            // request data
            var mode = chart_settings.mode;
            if (mode == 'execute') {
                self.app.jobs.submit(chart, self._defaultRequestString(chart), function() {
                    view.plot(chart, self._defaultRequestDictionary(chart))
                });
            } else {
                view.plot(chart, self._defaultRequestDictionary(chart))
            }
        });
    },
    
    // remove
    _removeChart: function(id) {
        var item = this.list[id];
        if (item) {
            // remove svg element
            item.svg.remove();
            
            // find div element (if any)
            item.$el.remove();
        }
    },
    
    // template
    _template: function(options) {
        return '<div id="' + options.id.substr(1) + '" class="item">' +
                    '<span id="info">' +
                        '<span id="icon" style="font-size: 1.2em; display: inline-block;"/>' +
                        '<span id="text" style="position: relative; margin-left: 5px; top: -1px; font-size: 1.0em;"/>' +
                    '</span>' +
                    '<svg style="height: ' + options.height + 'px;"/>' +
                '</div>';
    },
    
    // create default chart request
    _defaultRequestString : function(chart) {
    
        // get chart settings
        var chart_settings  = this.app.types.get(chart.get('type'));
       
        // configure request
        var request_string = '';
        
        // add groups to data request
        var group_index = 0;
        chart.groups.each(function(group) {
            for (var key in chart_settings.columns) {
                request_string += key + '_' + (++group_index) + ':' + group.get(key) + ', ';
            }
        });
        
        // return
        return 'columns : 2';
        //return request_string.substring(0, request_string.length - 2);
    },
    
    // create default chart request
    _defaultRequestDictionary : function(chart) {
    
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