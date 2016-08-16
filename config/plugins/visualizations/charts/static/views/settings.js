/**
 *  This class renders the chart configuration form.
 */
define( [ 'mvc/ui/ui-table', 'mvc/ui/ui-misc', 'mvc/form/form-parameters', 'utils/utils', 'mvc/form/form-view' ], function( Table, Ui, Parameters, Utils, Form ) {
    return Backbone.View.extend({
        initialize: function( app, options ) {
            var self = this;
            this.app = app;
            this.chart = this.app.chart;
            this.setElement( '<div/>' );
            this.chart.on( 'change', function() { self.render() } );
        },

        render: function() {
            this.form = new Form( { inputs: this.chart.definition.settings, cls: 'ui-portlet-plain' } );
            this.$el.empty().append( this.form.$el );
        }
    });
});