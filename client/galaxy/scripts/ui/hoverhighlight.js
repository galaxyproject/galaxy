(function (factory) {
    if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else {
        // Browser globals
        factory(jQuery);
    }

}(function () {
//=============================================================================

    jQuery.fn.extend({
        hoverhighlight : function $hoverhighlight( scope, color ){
            scope = scope || 'body';
            if( !this.length ){ return this; }

            $( this ).each( function(){
                var $this = $( this ),
                    targetSelector = $this.data( 'target' );

                if( targetSelector ){
                    $this.mouseover( function( ev ){
                        $( targetSelector, scope ).css({
                            background: color
                        });
                    })
                    .mouseout( function( ev ){
                        $( targetSelector ).css({
                            background: ''
                        });
                    });
                }
            });
            return this;
        }
    });
}));
