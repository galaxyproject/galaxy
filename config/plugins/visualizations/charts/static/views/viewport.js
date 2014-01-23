// dependencies
define(['library/portlet', 'library/ui', 'library/utils'],
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
        this.portlet = new Portlet({
            label       : '',
            icon        : 'fa-signal',
            height      : this.options.height,
            overflow    : 'hidden',
            operations  : {
                'edit'  : new Ui.ButtonIcon({
                    icon    : 'fa-gear',
                    tooltip : 'Configure'
                })
            }
        });
        
        // set this element
        this.setElement(this.portlet.$el);
        
        // events
        var self = this;
        
        // add
        this.app.charts.on('add', function(chart) {
            self._addChart(chart);
        });
        
        // remove
        this.app.charts.on('remove', function(chart) {
            self._removeChart(chart.id);
        });
        
        // replace
        this.app.charts.on('change', function(chart) {
            self._removeChart(chart.id);
            self._addChart(chart);
        });
    },
    
    // show
    show: function(chart_id) {
        // hide all
        this.$el.find('svg').hide();
        
        // identify selected item from list
        var item = this.list[chart_id];
        if (item) {
            // show selected chart
            this.$el.find(item.svg_id).show();
        
            // get chart
            var chart = self.app.charts.get(chart_id);
                
            // update portlet
            this.portlet.label(chart.get('title'));
            this.portlet.setOperation('edit', function() {
                // get chart
                self.app.chart.copy(chart);
                
                // show edit
                self.app.charts_view.$el.hide();
                self.app.chart_view.$el.show();
            });
        
            // this trigger d3 update events
            $(window).trigger('resize');
        }
    },
    
    // add
    _addChart: function(chart) {
        // link this
        var self = this;
        
        // backup chart details
        var chart_id = chart.id;
    
        // make sure that svg does not exist already
        this._removeChart(chart_id);
            
        // create id
        var svg_id = '#svg_' + chart_id;
        
        // create element
        var chart_el = $(this._template({id: svg_id, height : this.options.height}));
        
        // add to portlet
        this.portlet.append(chart_el);
        
        // backup id
        this.list[chart_id] = {
            svg_id : svg_id
        }
        
        // identify chart type
        var chart_type = chart.get('type');
        var chart_settings = this.app.types.get(chart_type);
            
        // create chart view
        var self = this;
        require(['charts/' + chart_type], function(ChartView) {
            // create chart
            var view = new ChartView(self.app, {svg_id : svg_id, chart : chart});
            
            // reset chart data
            var chart_data = [];
            
            // request data
            var chart_index = 0;
            chart.groups.each(function(group) {

                // add group data
                chart_data.push({
                    key     : (chart_index + 1) + ':' + group.get('label'),
                    values  : []
                });
                    
                // get data
                for (var key in chart_settings.data) {
                    // configure request
                    var data_options = {
                        view        : view,
                        data        : chart_data,
                        index       : chart_index,
                        dataset_id  : group.get('dataset_id'),
                        column      : group.get(key),
                        column_key  : key
                    }
                    
                    // make request
                    self._data(data_options);
                }
        
                // count
                chart_index++;
            });
            
            // show
            self.show(chart_id);
        });
    },
    
    // data
    _data: function(options) {
        // gather objects
        var view        = options.view;
        var data        = options.data;
        
        // gather parameters
        var index       = options.index;
        var column      = options.column;
        var dataset_id  = options.dataset_id;
        var column_key  = options.column_key;
        var group_data  = data[options.index];
        
        // send request
        self.app.datasets.get({id : dataset_id, column: column}, function(dataset) {
            // select column
            var values = dataset.values[column];
            var n_values = values.length;
            
            // read column values
            var column_values = [];
            for (var i = 0; i < n_values; i++) {
                var value = values[i];
                if(!isNaN(value)) {
                    column_values.push(value);
                } else {
                    column_values.push(0)
                }
            }
             
            // write column values
            for (var i = 0; i < n_values; i++) {
                // make sure dictionary exists
                if (group_data.values[i] === undefined) {
                    group_data.values[i] = {
                        x : i,
                        y : 0
                    }
                }
                    
                // write data
                group_data.values[i][column_key] = column_values[i];
            }
            
            // refresh view
            view.refresh(data);
        });

    },
    
    // remove
    _removeChart: function(id) {
        var item = this.list[id];
        if (item) {
            d3.select(item.svg_id).remove();
            $(item.svg_id).remove();
        }
    },
    
    // template
    _template: function(options) {
        return '<svg id="' + options.id.substr(1) + '"style="height: ' + options.height + 'px;"></svg>';
    }
});

});