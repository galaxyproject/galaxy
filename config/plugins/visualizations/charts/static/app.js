// dependencies
define(['mvc/ui/ui-modal', 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc', 'utils/utils',
        'plugin/library/jobs', 'plugin/library/datasets', 'plugin/library/storage', 'plugin/library/deferred',
        'plugin/views/viewer', 'plugin/views/editor',
        'plugin/models/config', 'plugin/models/chart',
        'plugin/charts/types'],
        function(   Modal, Portlet, Ui, Utils, Jobs, Datasets, Storage, Deferred,
                    ViewerView, EditorView,
                    Config, Chart, Types
                ) {

/**
 *  Main application class.
 */
return Backbone.View.extend({
    // initialize
    initialize: function(options){
        // deactivate all debugs outputs
        //window.console.debug = function() {};
        
        // link options
        this.options = options;

        // link galaxy modal or create one
        if (Galaxy && Galaxy.modal) {
            this.modal = Galaxy.modal;
        } else {
            this.modal = new Modal.View();
        }
        
        //
        // models
        //
        this.config = new Config();
        this.types = new Types();
        this.chart = new Chart();
        
        //
        // libraries
        //
        this.jobs = new Jobs(this);
        this.datasets = new Datasets(this);
        this.storage = new Storage(this);
        this.deferred = new Deferred();
        
        //
        // views
        //
        this.viewer_view = new ViewerView(this);
        this.editor_view = new EditorView(this);
        
        // append views
        this.$el.append(this.viewer_view.$el);
        this.$el.append(this.editor_view.$el);
        
        // pick start screen
        if (!this.storage.load()) {
            // show editor
            this.go('editor');
        } else {
            // show viewport
            this.go('viewer');
            
            // draw chart
            var self = this;
            this.deferred.execute(function() {
                self.chart.trigger('redraw');
            });
        }
    },
    
    // loads a view and makes sure that all others are hidden
    go: function(view_id) {
        // hide all tooltips
        $('.tooltip').hide();
        
        // pick view
        switch (view_id) {
            case 'editor' :
                this.editor_view.show();
                this.viewer_view.hide();
                break;
            case 'viewer' :
                this.editor_view.hide();
                this.viewer_view.show();
                break;
        }
    },
    
    // get root path
    chartPath: function(chart_type) {
        // create path from id
        var path = chart_type.split(/_(.+)/);
        
        // check path
        if (path.length >= 2) {
            // return path
            return path[0] + '/' + path[1];
        } else {
            // log status
            console.debug('FAILED App:chartPath() - Invalid format: ' + chart_type);
        }
        return undefined;
    }
});

});