/* This class renders the chart configuration form. */
define( [ 'mvc/form/form-view' ], function( Form ) {
    return Backbone.View.extend({
        initialize: function( app, options ) {
            var self = this;
            this.chart = app.chart;
            this.setElement( '<div/>' );
            this.chart.on( 'change', function() { self.render() } );
        },
        render: function() {
            var self = this;
            this.form = new Form({
                inputs   : this.chart.definition.settings,
                cls      : 'ui-portlet-plain',
                onchange : function() { self.chart.settings.set( self.form.data.create() ); }
            });
            this.form.set( this.chart.settings.attributes );
            this.$el.empty().append( this.form.$el );
        }
    });
});