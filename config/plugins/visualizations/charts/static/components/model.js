define( [ 'utils/utils' ], function( Utils ) {
    return Backbone.Model.extend({
        defaults : {
            id              : null,
            title           : '',
            type            : '',
            date            : null,
            state           : '',
            state_info      : '',
            modified        : false,
            dataset_id      : '',
            dataset_id_job  : ''
        },

        initialize: function( options ) {
            this.groups     = new Backbone.Collection();
            this.settings   = new Backbone.Model();
            this.definition = {};
        },

        reset: function( options ) {
            this.set({
                id            : Utils.uid(),
                type          : '__first',
                dataset_id    : options.config.dataset_id,
                title         : 'New Chart'
            });
            this.settings.clear();
            this.groups.reset();
            this.groups.add( { id : Utils.uid() } );
        },

        state: function( value, info ) {
            this.set( { state : value, state_info : info } );
            this.trigger( 'set:state' );
            console.debug( 'Chart:state() - ' + info + ' (' + value + ')' );
        }
    });
});