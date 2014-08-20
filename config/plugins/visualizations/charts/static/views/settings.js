// dependencies
define(['mvc/ui/ui-misc', 'plugin/library/ui-table-form', 'utils/utils'],
        function(Ui, TableForm, Utils) {

/**
 *  This class renders the chart configuration form.
 */
return Backbone.View.extend({
    // initialize
    initialize: function(app, options) {
        // link app
        this.app = app;
        
        // link this
        var self = this;
        
        // get current chart object
        this.chart = this.app.chart;
        
        // create settings
        this.form = new TableForm.View(app, {
            title   : 'Configuration',
            content : 'This chart type does not provide any options.'
        });
        
        // set element
        this.setElement(this.form.$el);
        
        // change
        var self = this;
        this.chart.on('change', function() {
            self._refresh();
        });
    },
    
    // update dataset
    _refresh: function() {
        // get settings
        var chart_definition = this.chart.definition;
        
        // check if chart definition is available
        if (!chart_definition) {
            return;
        }
        
        // set title
        this.form.title(chart_definition.category + ' - ' + chart_definition.title + ':');
        
        // update table form model
        this.form.update(chart_definition.settings, this.chart.settings);
    }
});

});