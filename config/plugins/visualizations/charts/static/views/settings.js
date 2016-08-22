/** This class renders the chart configuration form. */
define( [ 'utils/utils', 'mvc/ui/ui-misc', 'mvc/form/form-view', 'mvc/form/form-data', 'plugin/views/description' ], function( Utils, Ui, Form, FormData, Description ) {
    return Backbone.View.extend({
        initialize: function( app, options ) {
            var self = this;
            this.app = app;
            this.chart = app.chart;
            this.description = new Description( this.app );
            this.message = new Ui.Message( { message: 'There are no options for this chart type.', persistent: true, status: 'info' } );
            this.setElement( $( '<div/>' ).append( this.description.$el ).append( this.message.$el ).append( this.$form = $( '<div/>' ) ) );
            this.listenTo( this.chart, 'change', function() { self.render() } );
        },
        render: function() {
            var self = this;
            var inputs = Utils.clone( this.chart.definition.settings );
            if ( _.size( inputs ) > 0 ) {
                FormData.visitInputs( inputs, function( input, name ) {
                    var model_value = self.chart.settings.get( name );
                    model_value !== undefined && !input.hidden && ( input.value = model_value );
                });
                this.form = new Form({
                    inputs   : inputs,
                    cls      : 'ui-portlet-plain',
                    onchange : function() { self.chart.settings.set( self.form.data.create() ); }
                });
                this.$form.empty().append( this.form.$el );
                this.message.$el.hide();
            } else {
                this.$form.empty();
                this.message.$el.show();
            }
        }
    });
});