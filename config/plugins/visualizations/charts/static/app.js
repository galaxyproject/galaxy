// dependencies
define(['library/portlet', 'library/ui', 'library/utils',
        'views/charts', 'views/viewport', 'views/chart', 'views/group',
        'models/config', 'models/datasets', 'models/chart', 'models/charts', 'models/group', 'models/types'],
        function(   Portlet, Ui, Utils,
                    ChartsView, ViewportView, ChartView, GroupView,
                    Config, Datasets, Chart, Charts, Group, Types
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
        
        // create configuration model
        this.config = new Config();
        
        // create chart models
        this.types = new Types();
        this.chart = new Chart();
        this.charts = new Charts();
        this.group = new Group();
        
        // create dataset handler
        this.datasets = new Datasets(this);
        
        // create views
        this.charts_view = new ChartsView(this);
        this.group_view = new GroupView(this);
        this.chart_view = new ChartView(this);
        this.viewport_view = new ViewportView(this);
        
        // append view port to charts viewer
        this.charts_view.append(this.viewport_view.$el);
            
        // create portlet
        if (!this.options.config.widget) {
            this.portlet = new Portlet({icon : 'fa-bar-chart-o', label : 'Charts'});
        } else {
            this.portlet = $('<div></div>');
        }
        
        // append views
        this.portlet.append(this.charts_view.$el);
        this.portlet.append(this.group_view.$el);
        this.portlet.append(this.chart_view.$el);
        
        // set element
        if (!this.options.config.widget) {
            this.setElement(this.portlet.$el);
        } else {
            this.setElement(this.portlet);
        }
        
        // hide views
        this.group_view.$el.hide();
        this.charts_view.$el.hide();
        
        // events
        var self = this;
        this.config.on('change:current_view', function() {
            self._showCurrent();
        });
    },
    
    // current view
    _showCurrent: function() {
        
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