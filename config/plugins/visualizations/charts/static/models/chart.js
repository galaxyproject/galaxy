define( [ 'utils/utils' ], function( Utils ) {
    var Groups = Backbone.Collection.extend({
        model: Backbone.Model.extend({
            defaults : {
                key     : 'Data label',
                date    : ''
            },

            reset: function(){
                this.clear( { silent: true } ).set( this.defaults );
                this.trigger( 'reset', this );
            }
        })
    });
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
            this.groups = new Groups();
            this.settings = new Backbone.Model();
        },

        reset: function( options ) {
            this.set({
                'id'            : Utils.uid(),
                'type'          : 'nvd3_bar',
                'dataset_id'    : options.config.dataset_id,
                'title'         : 'New Chart'
            });
            this.settings.clear();
            this.groups.reset();
            this.groups.add( { id : Utils.uid() } );
        },

        state: function( value, info ) {
            this.set( { 'state': value, 'state_info': info } );
            this.trigger( 'set:state' );
            console.debug( 'Chart:state() - ' + info + ' (' + value + ')' );
        }
    });
});