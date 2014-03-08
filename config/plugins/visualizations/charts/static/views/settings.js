// dependencies
define(['plugin/library/ui', 'plugin/library/ui-table-form', 'utils/utils'],
        function(Ui, TableForm, Utils) {

// widget
return Backbone.View.extend(
{
    // initialize
    initialize: function(app, options) {
        // link app
        this.app = app;
        
        // link this
        var self = this;
        
        // get current chart object
        this.chart = this.app.chart;
        
        this.form = new TableForm.View({
            title   : 'Chart options:',
            content : 'This chart type does not provide any options.'
        });
        
        // set element
        this.setElement(this.form.$el);
        
        // change
        var self = this;
        this.chart.on('change', function() {
            self._refreshTable();
        });
    },
    
    // update dataset
    _refreshTable: function() {
        // identify datasets
        var chart_type = this.chart.get('type');
        
        // check if dataset is available
        if (!chart_type) {
            return;
        }
        
        // update table form model
        var chart_definition = this.app.types.get(chart_type);
        this.form.update(chart_definition.settings, this.chart.settings);
    }
});

});