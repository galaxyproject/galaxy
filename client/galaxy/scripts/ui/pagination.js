// from: https://raw.githubusercontent.com/umdjs/umd/master/jqueryPlugin.js
// Uses AMD or browser globals to create a jQuery plugin.
(function (factory) {
    if (typeof define === 'function' && define.amd) {
        // AMD. Register as an anonymous module.
        define(['jquery'], factory);
    } else {
        // Browser globals
        factory(jQuery);
    }

}(function ($) {

    /** Builds (twitter bootstrap styled) pagination controls.
     *  If the totalDataSize is not null, a horizontal list of page buttons is displayed.
     *  If totalDataSize is null, two links ('Prev' and 'Next) are displayed.
     *  When pages are changed, a 'pagination.page-change' event is fired
     *      sending the event and the (0-based) page requested.
     */
    function Pagination( element, options ){
        /** the total number of pages */
        this.numPages = null;
        /** the current, active page */
		this.currPage = 0;
		return this.init( element, options );
    }

    /** data key under which this object will be stored in the element */
	Pagination.prototype.DATA_KEY = 'pagination';
    /** default options */
    Pagination.prototype.defaults = {
        /** which page to begin at */
        startingPage    : 0,
        /** number of data per page */
        perPage         : 20,
        /** the total number of data (null == unknown) */
        totalDataSize   : null,
        /** size of current data on current page */
        currDataSize    : null
	};

    /** init the control, calc numPages if possible, and render
     *  @param {jQuery} the element that will contain the pagination control
     *  @param {Object} options a map containing overrides to the pagination default options
     */
	Pagination.prototype.init = function _init( $element, options ){
		options = options || {};
		this.$element = $element;
		this.options = jQuery.extend( true, {}, this.defaults, options );

        this.currPage = this.options.startingPage;
        if( this.options.totalDataSize !== null ){
            this.numPages = Math.ceil( this.options.totalDataSize / this.options.perPage );
            // limit currPage by numPages
            if( this.currPage >= this.numPages ){
                this.currPage = this.numPages - 1;
            }
        }
        //console.debug( 'Pagination.prototype.init:', this.$element, this.currPage );
        //console.debug( JSON.stringify( this.options ) );

        // bind to data of element
        this.$element.data( Pagination.prototype.DATA_KEY, this );

        this._render();
		return this;
	};

    /** helper to create a simple li + a combo */
    function _make$Li( contents ){
        return $([
            '<li><a href="javascript:void(0);">', contents, '</a></li>'
        ].join( '' ));
    }

    /** render previous and next pagination buttons */
    Pagination.prototype._render = function __render(){
        // no data - no pagination
        if( this.options.totalDataSize === 0 ){ return this; }
        // only one page
        if( this.numPages === 1 ){ return this; }

        // when the number of pages are known, render each page as a link
        if( this.numPages > 0 ){
            this._renderPages();
            this._scrollToActivePage();

        // when the number of pages is not known, render previous or next
        } else {
            this._renderPrevNext();
        }
		return this;
    };

    /** render previous and next pagination buttons */
    Pagination.prototype._renderPrevNext = function __renderPrevNext(){
        var pagination = this,
            $prev = _make$Li( 'Prev' ),
            $next = _make$Li( 'Next' ),
            $paginationContainer = $( '<ul/>' ).addClass( 'pagination pagination-prev-next' );

        // disable if it either end
        if( this.currPage === 0 ){
            $prev.addClass( 'disabled' );
        } else {
            $prev.click( function(){ pagination.prevPage(); });
        }
        if( ( this.numPages && this.currPage === ( this.numPages - 1 ) )
        ||  ( this.options.currDataSize && this.options.currDataSize < this.options.perPage ) ){
            $next.addClass( 'disabled' );
        } else {
            $next.click( function(){ pagination.nextPage(); });
        }

        this.$element.html( $paginationContainer.append([ $prev, $next ]) );
        //console.debug( this.$element, this.$element.html() );
        return this.$element;
    };

    /** render page links for each possible page (if we can) */
    Pagination.prototype._renderPages = function __renderPages(){
        // it's better to scroll the control and let the user see all pages
        //  than to force her/him to change pages in order to find the one they want (as traditional << >> does)
        var pagination = this,
            $scrollingContainer = $( '<div>' ).addClass( 'pagination-scroll-container' ),
            $paginationContainer = $( '<ul/>' ).addClass( 'pagination pagination-page-list' ),
            page$LiClick = function( ev ){
                pagination.goToPage( $( this ).data( 'page' ) );
            };

        for( var i=0; i<this.numPages; i+=1 ){
            // add html5 data tag 'page' for later click event handler use
            var $pageLi = _make$Li( i + 1 ).attr( 'data-page', i ).click( page$LiClick );
            // highlight the current page
            if( i === this.currPage ){
                $pageLi.addClass( 'active' );
            }
            //console.debug( '\t', $pageLi );
            $paginationContainer.append( $pageLi );
        }
        return this.$element.html( $scrollingContainer.html( $paginationContainer ) );
    };

    /** scroll scroll-container (if any) to show the active page */
    Pagination.prototype._scrollToActivePage = function __scrollToActivePage(){
        // scroll to show active page in center of scrollable area
        var $container = this.$element.find( '.pagination-scroll-container' );
        // no scroll container : don't scroll
        if( !$container.length ){ return this; }

        var $activePage = this.$element.find( 'li.active' ),
            midpoint = $container.width() / 2;
        //console.debug( $container, $activePage, midpoint );
        $container.scrollLeft( $container.scrollLeft() + $activePage.position().left - midpoint );
        return this;
    };

    /** go to a certain page */
    Pagination.prototype.goToPage = function goToPage( page ){
        if( page <= 0 ){ page = 0; }
        if( this.numPages && page >= this.numPages ){ page = this.numPages - 1; }
        if( page === this.currPage ){ return this; }

        //console.debug( '\t going to page ' + page )
        this.currPage = page;
        this.$element.trigger( 'pagination.page-change', this.currPage );
        //console.info( 'pagination:page-change', this.currPage );
        this._render();
        return this;
    };

    /** go to the previous page */
    Pagination.prototype.prevPage = function prevPage(){
        return this.goToPage( this.currPage - 1 );
    };

    /** go to the next page */
    Pagination.prototype.nextPage = function nextPage(){
        return this.goToPage( this.currPage + 1 );
    };

    /** return the current page */
    Pagination.prototype.page = function page(){
        return this.currPage;
    };

    // alternate constructor invocation
    Pagination.create = function _create( $element, options ){
        return new Pagination( $element, options );
    };

    // as jq plugin
    jQuery.fn.extend({
        pagination : function $pagination( options ){
			var nonOptionsArgs = jQuery.makeArray( arguments ).slice( 1 );

            // if passed an object - use that as an options map to create pagination for each selected
            if( jQuery.type( options ) === 'object' ){
                return this.map( function(){
                    Pagination.create( $( this ), options );
                    return this;
                });
            }

            // (other invocations only work on the first element in selected)
            var $firstElement = $( this[0] ),
                previousControl = $firstElement.data( Pagination.prototype.DATA_KEY );
            // if a pagination control was found for this element, either...
            if( previousControl ){
                // invoke a function on the pagination object if passed a string (the function name)
                if( jQuery.type( options ) === 'string' ){
                    var fn = previousControl[ options ];
                    if( jQuery.type( fn ) === 'function' ){
                        return fn.apply( previousControl, nonOptionsArgs );
                    }

                // if passed nothing, return the previously set control
                } else {
                    return previousControl;
                }
            }
            // if there is no control already set, return undefined
            return undefined;
        }
    });
}));
