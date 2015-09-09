define([ 'plugin/app' ], function( App ){
    return Backbone.View.extend({
        el: $( '#mrh-heatmap' ),

        initialize : function( options ){
            this.model = new App( options );
        },

        render : function(){

        },
    });
});