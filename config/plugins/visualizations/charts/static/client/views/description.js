/** This class renders the chart configuration form. */
define( [ 'utils/utils' ], function( Utils ) {
    return Backbone.View.extend({
        initialize: function( app, options ) {
            var self = this;
            this.chart = app.chart;
            this.app = app;
            this.setElement( this._template() );
            this.$title = this.$( '.charts-description-title' );
            this.$image = this.$( '.charts-description-image' );
            this.$text  = this.$( '.charts-description-text' );
            this.listenTo( this.chart, 'change', function() { self.render() } );
            this.render();
        },
        render: function() {
            if ( this.chart.get( 'type' ) ) {
                this.$image.attr( 'src', repository_root + '/visualizations/' + this.app.split( this.chart.get( 'type' ) ) + '/logo.png' );
                this.$title.html( this.chart.definition.title + ' (' + this.chart.definition.library + ')' );
                this.$text.html( Utils.linkify( this.chart.definition.description || '' ) );
                this.$el.show();
            } else {
                this.$el.hide();
            }
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