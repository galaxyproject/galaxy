// dependencies
define(['mvc/ui/ui-portlet', 'plugin/library/ui', 'utils/utils', 'plugin/library/jobs', 'plugin/library/datasets',
        'plugin/views/charts', 'plugin/views/chart',
        'plugin/models/config', 'plugin/models/chart', 'plugin/models/charts', 'plugin/models/types'],
        function(   Portlet, Ui, Utils, Jobs, Datasets,
                    ChartsView, ChartView,
                    Config, Chart, Charts, Types
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
        this.modal = Galaxy.modal;
        
        // create configuration model
        this.config = new Config();
        
        // job/data /processor
        this.jobs = new Jobs(this);
        
        // create chart models
        this.types = new Types();
        this.chart = new Chart();
        this.charts = new Charts();
        
        // create dataset handler
        this.datasets = new Datasets(this);
        
        // create views
        this.charts_view = new ChartsView(this);
        this.chart_view = new ChartView(this);
        
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
        var title = this.config.get('title');
        if (title) {
            title = ' - ' + title;
        }
        this.portlet.title('Charts' + title);
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