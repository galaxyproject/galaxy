define( [], function() {
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

        reset: function() {
            this.clear( { silent: true } ).set( this.defaults );
            this.groups.reset();
            this.settings.clear();
            this.trigger( 'reset', this );
        },

        copy: function( new_chart ) {
            var current = this;
            current.clear( { silent: true } ).set( this.defaults );
            current.set( new_chart.attributes );
            current.settings = new_chart.settings.clone();
            current.groups.reset();
            new_chart.groups.each( function( group ) {
                current.groups.add( group.clone() );
            });
            current.trigger( 'change', current );
        },

        state: function( value, info ) {
            this.set( { 'state': value, 'state_info': info } );
            this.trigger( 'set:state' );
            console.debug( 'Chart:state() - ' + info + ' (' + value + ')' );
        }
    });
});