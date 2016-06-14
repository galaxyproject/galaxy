define( [], function() {
    return Backbone.Model.extend({
        defaults : {
            key     : 'Data label',
            date    : ''
        },

        reset: function(){
            this.clear( { silent: true } ).set( this.defaults );
            this.trigger( 'reset', this );
        }
    });
});