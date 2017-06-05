/** This class renders the page list. */
define( [ 'mvc/grid/grid-view' ], function( GridView ) {
    var View = Backbone.View.extend({
        initialize: function( options ) {
            this.setElement( $( '<div/>' ) );
            grid = new GridView( { url_base: Galaxy.root + 'page/list', dict_format: true } );
            this.$el.append( grid.$el );
        },

        render: function() {
        }
    });

    return {
        View: View
    }
});