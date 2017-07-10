
define( [ 'utils/utils' ], function( Utils ) {

    /** Dataset edit attributes view */
    var View = Backbone.View.extend({

        initialize: function( dataset_id ) {
            this.setElement( '<div/>' );
            this.render( dataset_id );
        },

        render: function( dataset_id ) {
        }
    });

    return {
        View  : View
    };
});
