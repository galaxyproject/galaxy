// dependencies
define(['library/portlet', 'library/ui', 'library/utils',
        'main', 'viewport', 'create', 'config',
        'models/datasets', 'models/chart', 'models/charts', 'models/types'],
        function(   Portlet, Ui, Utils,
                    Main, Viewport, Create, Config,
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
        
        // create chart objects
        this.types = new Types();
        this.chart = new Chart();
        this.charts = new Charts(this);
        
        // create dataset handler
        this.datasets = new Datasets(this);
        
        // create views
        this.main = new Main(this);
        this.viewport = new Viewport(this);
        this.config = new Config(this);
        this.create = new Create(this);
        
        // portlet
        this.portlet = new Portlet({icon : 'fa-bar-chart-o', label : 'Charts'});
        this.portlet.append(this.main.$el);
        this.portlet.append(this.config.$el);
        this.portlet.append(this.create.$el);
        
        // append main
        this.main.append(this.viewport.$el);
        
        // create
        this.config.$el.hide();
        this.create.$el.hide();
        
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