// dependencies
define(['mvc/ui/ui-portlet', 'plugin/library/ui', 'utils/utils',
        'plugin/views/charts', 'plugin/views/viewport', 'plugin/views/chart',
        'plugin/models/config', 'plugin/models/datasets', 'plugin/models/chart', 'plugin/models/charts', 'plugin/models/types'],
        function(   Portlet, Ui, Utils,
                    ChartsView, ViewportView, ChartView,
                    Config, Datasets, Chart, Charts, Types
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
        
        // create dataset handler
        this.datasets = new Datasets(this);
        
        // create views
        this.charts_view = new ChartsView(this);
        this.chart_view = new ChartView(this);
        this.viewport_view = new ViewportView(this);
        
        // append view port to charts viewer
        this.charts_view.append(this.viewport_view.$el);
            
        // create portlet
        if (!this.options.config.widget) {
            this.portlet = new Portlet.View({icon : 'fa-bar-chart-o'});
        } else {
            this.portlet = $('<div></div>');
        }
        
        // append views
        this.portlet.append(this.charts_view.$el);
        this.portlet.append(this.chart_view.$el);

        // set element
        if (!this.options.config.widget) {
            this.setElement(this.portlet.$el);
        } else {
            this.setElement(this.portlet);
        }
        
        // hide views
        this.charts_view.$el.hide();
        
        // events
        var self = this;
        this.config.on('change:current_view', function() {
            self._showCurrent();
        });
        this.config.on('change:title', function() {
            self._refreshTitle();
        });
        
        // render
        this.render();
    },
    
    // render
    render: function() {
        this._refreshTitle();
    },
    
    // refresh title
    _refreshTitle: function() {
        this.portlet.title('Charts - ' + this.config.get('title'));
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