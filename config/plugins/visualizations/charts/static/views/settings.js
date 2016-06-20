/**
 *  This class renders the chart configuration form.
 */
define([ 'mvc/ui/ui-misc', 'plugin/library/ui-table-form', 'utils/utils' ], function( Ui, TableForm, Utils ) {
    return Backbone.View.extend({
        initialize: function(app, options) {
            var self = this;
            this.app = app;
            this.chart = this.app.chart;
            this.form = new TableForm.View( app, {
                title   : 'Configuration',
                content : 'This chart type does not provide any options.'
            });
            this.setElement( this.form.$el );
            this.chart.on( 'change', function() { self._refresh() } );
        },

        /** Update dataset */
        _refresh: function() {
            var chart_definition = this.chart.definition;
            if ( chart_definition ) {
                this.form.title( chart_definition.category + ' - ' + chart_definition.title + ':' );
                this.form.update( chart_definition.settings, this.chart.settings );
            }
        }
    });
});