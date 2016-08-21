/** This class renders the chart configuration form. */
define( [ 'utils/utils', 'mvc/form/form-view', 'mvc/form/form-data' ], function( Utils, Form, FormData ) {
    return Backbone.View.extend({
        initialize: function( app, options ) {
            var self = this;
            this.chart = app.chart;
            this.setElement( '<div/>' );
            this.chart.on( 'change', function() { self.render() } );
        },
        render: function() {
            var self = this;
            var inputs = Utils.clone( this.chart.definition.settings );
            FormData.visitInputs( inputs, function( input, name ) {
                var model_value = self.chart.settings.get( name );
                model_value !== undefined && !input.hidden && ( input.value = model_value );
            });
            this.form = new Form({
                inputs   : inputs,
                cls      : 'ui-portlet-plain',
                onchange : function() { self.chart.settings.set( self.form.data.create() ); }
            });
            this.chart.settings.set( self.form.data.create() );
            this.$el.empty().append( this.form.$el );
        }
    });
});