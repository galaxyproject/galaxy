/** This class renders the page list. */
define( [ 'utils/utils', 'mvc/grid/grid-view' ], function( Utils, GridView ) {
    var View = Backbone.View.extend({
        initialize: function( options ) {
            var self = this;
            this.setElement( $( '<div/>' ) );
            this.model = new Backbone.Model();
            Utils.get({
                url     : Galaxy.root + 'page/list',
                success : function( response ) {
                    response[ 'dict_format' ] = true;
                    self.model.set( response );
                    self.render();
                }
            });
        },

        render: function() {
            grid = new GridView( this.model.attributes );
            this.$el.empty().append( grid.$el );
        }
    });

    return {
        View: View
    }
});