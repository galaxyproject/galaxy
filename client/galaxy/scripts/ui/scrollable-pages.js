(function( $ ){
    "use strict";

    var DATA_KEY = 'scrollable-pages';
    var defaultOptions = {
        force : 5,
        pageSelector : '> li',
    };

    function roundTo( x, roundedTo ){
        var mod = x % roundedTo;
        var over = mod > ( roundedTo / 2 );
        return over? ( x + roundedTo - mod ) : ( x - mod );
    }

    var ScrollablePages = function( element, options ){
        this.$el = $( element );
        this._init( options );
    };

    ScrollablePages.prototype._init = function( options ){
        var self = this;
        self.options = $.extend( {}, defaultOptions, options );
        self._inertia = 0;
        self.currentPage = 0;

        // self._addStyles();

        // when the window is resized, we need to recalc the viewport
        $( window ).resize( function(){
            self.updateViewport();
        });
        this.updateViewport();

        // set up raf to handle the psuedo-physics
        function frame( time ){
            self._gravitate();
            requestAnimationFrame( frame );
        }
        requestAnimationFrame( frame );

        self.$el.trigger( $.Event( DATA_KEY + '.init', {
            options: options
        }));
    };

    // ScrollablePages.prototype._addStyles = function(){
    //     var self = this;
    //     self.$el.css({
    //         'overflow-x': 'auto',
    //         'overflow-y': 'hidden',
    //     });
    //     self.$el.find( self.options.pageSelector ).css({
    //         display     : 'inline-block',
    //         'overflow-x': 'hidden',
    //         'overflow-y': 'auto',
    //     });
    // };

    ScrollablePages.prototype.updateViewport = function(){
        this.viewportWidth = this.$el.innerWidth();
        console.log( 'viewportWidth:', this.viewportWidth );

        var $pages = this.$el.find( this.options.pageSelector );
        this.numberOfPages = $pages.length;
        // if webkit behaved like FF when the li's are flex: 1 0 auto;...
        // we could remove this *and* the resize listener that calls it
        $pages.innerWidth( this.viewportWidth );

        this.$el.trigger( $.Event( DATA_KEY + '.update-viewport', {
            viewportWidth: this.viewportWidth,
            numberOfPages: this.numberOfPages
        }));
    };

    ScrollablePages.prototype._gravitate = function(){
        var self = this;
        var currScroll = self.$el.scrollLeft();
        var gravitateTo = roundTo( currScroll, self.viewportWidth );

        if( currScroll !== gravitateTo ){
            var dir = currScroll < gravitateTo? 1 : -1;
            var whereToNext = currScroll + self._inertia + ( dir * self.options.force );
            whereToNext = dir === 1?
                Math.min( whereToNext, gravitateTo ):
                Math.max( whereToNext, gravitateTo );

            self.$el.scrollLeft( whereToNext );
            self._inertia += dir;

        } else {
            self._inertia = 0;

            var thisPage = Math.floor( gravitateTo / self.viewportWidth );
            if( self.currentPage !== thisPage ){
                // scrollLeft( gravitateTo )?
                console.log( 'page change:', thisPage );
                self.$el.trigger( $.Event( DATA_KEY + '.page-change', {
                    oldPage: self.currentPage,
                    newPage: thisPage,
                }));
                self.currentPage = thisPage;
            }
        }
    };

    ScrollablePages.prototype.goToPage = function( page ){
        return this.$el.scrollLeft( page * this.viewportWidth );
    };

    $.fn.scrollablePages = function( options ){
        console.log( 'scrollablePages:', this.length );
        var objects = this.each( function(){
            var $this = $( this );
            var data = $this.data( DATA_KEY );
            if( !data ){
                data = new ScrollablePages( this );
                $this.data( DATA_KEY, data, options );
            }
        });
        if( typeof options !== 'string' ){
            return objects;
        }
        return objects.toArray().map( function( obj ){
            var data = $( obj ).data( DATA_KEY );
            var argsTail = $.makeArray( arguments ).slice( 1 );
            var attr = data[ options ];
            return typeof attr === 'function'? ( data[ options ].apply( data, argsTail ) ): attr;
        });
    };

    $.fn.scrollablePages.Constructor = ScrollablePages;

}( window.jQuery ));
