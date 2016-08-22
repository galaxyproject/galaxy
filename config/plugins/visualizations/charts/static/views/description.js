/** This class renders the chart configuration form. */
define( [], function() {
    return Backbone.View.extend({
        initialize: function( app, options ) {
            var self = this;
            this.chart = app.chart;
            this.app = app;
            this.setElement( this._template() );
            this.$title = this.$( '.charts-description-title' );
            this.$image = this.$( '.charts-description-image' );
            this.$text  = this.$( '.charts-description-text' );
            this.listenTo( this.chart, 'change:type', function() { self.render() } );
            this.render();
        },
        render: function() {
            this.$image.attr( 'src', app_root + 'charts/' + this.app.split( this.chart.get( 'type' ) ) + '/logo.png' );
            this.$title.html( this.chart.definition.title + ' (' + this.chart.definition.library + ')' );
            this.$text.html( this.chart.definition.description || this.chart.definition.category );
        },
        _template: function() {
            return  '<div class="charts-description">' +
                        '<table>' +
                            '<tr>' +
                                '<td class="charts-description-image-td">' +
                                    '<img class="charts-description-image"/>' +
                                '</td>' +
                                '<td>' +
                                    '<div class="charts-description-title ui-form-info"/>' +
                                    '<div class="charts-description-text ui-form-info"/>' +
                                '</td>' +
                            '</tr>' +
                        '</table>' +
                    '</div>';
        }
    });
});