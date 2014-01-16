// dependencies
define(['library/portlet', 'library/ui', 'library/utils',
        'views/charts', 'views/viewport', 'views/chart', 'views/group',
        'models/datasets', 'models/chart', 'models/charts', 'models/types'],
        function(   Portlet, Ui, Utils,
                    ChartsView, ViewportView, ChartView, GroupView,
                    Datasets, Chart, Charts, Types
                ) {

// widget
return Backbone.View.extend(
{
    // initialize
    initialize: function(options)
    {
        // link options
        this.options = options;
    
        // link galaxy
        this.modal = parent.Galaxy.modal;
        
        // create chart models
        this.types = new Types();
        this.chart = new Chart();
        this.charts = new Charts();
        
        // create dataset handler
        this.datasets = new Datasets(this);
        
        // create views
        this.charts_view = new ChartsView(this);
        this.group_view = new GroupView(this);
        this.chart_view = new ChartView(this);
        this.viewport_view = new ViewportView(this);
        
        // portlet
        this.portlet = new Portlet({icon : 'fa-bar-chart-o', label : 'Charts'});
        this.portlet.append(this.charts_view.$el);
        this.portlet.append(this.group_view.$el);
        this.portlet.append(this.chart_view.$el);
        
        // append main
        this.charts_view.append(this.viewport_view.$el);
        
        // create
        this.group_view.$el.hide();
        this.charts_view.$el.hide();
        
        // set elements
        this.setElement(this.portlet.$el);
    },
    
    // execute command
    execute: function(options) {
    },
    
    // unload
    onunload: function() {
    },
    
    // log
    log: function(location, message) {
        console.log(location + ' ' + message);
    }
});

});