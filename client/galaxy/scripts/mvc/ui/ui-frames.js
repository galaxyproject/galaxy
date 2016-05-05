/** Scratchbook viewer */
define([], function() {
var View = Backbone.View.extend({
    defaultOptions: {
        frame: {            // default frame size in cells
            cols : 6,
            rows : 3
        },
        rows        : 1000, // maximum number of rows
        cell        : 130,  // cell size in px
        margin      : 5,
        scroll      : 5,    // scroll speed
        top_min     : 40,   // top margin
        frame_max   : 9,    // maximum number of frames
        visible     : true, // initial visibility
    },

    cols            : 0,    // number of columns
    top             : 0,    // scroll/element top
    top_max         : 0,    // viewport scrolling state
    frame_z         : 0,    // frame z-index
    frame_counter   : 0,    // frame counter
    frame_uid       : 0,
    frame_list      : {},   // list of all frames
    frame_shadow    : null,
    visible         : false,
    event           : {},
    idle_counter    : 0,
    idle_timer	    : null,
    interval        : 1000, // interval to increment idle counter
    idle_interval   : 7, // frame idle interval
    skip_datatypes  : ['bigwig', 'bigbed', 'bam', 'rdata', 'sff', 'bcf'], // skip these items
    data_target_frame : 'data-target-frame',

    initialize : function( options ) {
        var self = this;
        this.options = _.defaults( options || {}, this.defaultOptions );
        this.visible = this.options.visible;
        this.top = this.top_max = this.options.top_min;
        this.setElement( $( '<div/>' ).addClass( 'galaxy-frame' ) );
        this.$el.append( $( '<div/>' ).addClass( 'frame-background' ) );
        this.$el.append( $( '<div/>' ).addClass( 'frame-menu frame-scroll-up fa fa-chevron-up fa-2x' ) );
        this.$el.append( $( '<div/>' ).addClass( 'frame-menu frame-scroll-down fa fa-chevron-down fa-2x' ) );
        this.$el.append( $( '<div/>' ).addClass( 'frame-shadow corner' ).attr( 'id', 'frame-shadow' ) );

        // initialize shadow to guiding drag/resize events
        this.frame_shadow = {
            id              : '#frame-shadow',
            screen_location : {},
            grid_location   : {},
            grid_rank       : null,
            grid_lock       : false
        };
        this._frameResize( this.frame_shadow, { width: 0, height: 0 } );
        this.frame_list[ '#frame-shadow' ] = this.frame_shadow;

        // initialize panel
        this.visible ? this.show() : this.hide();
        this._panelRefresh();
        $( window ).resize( function() { self.visible && self._panelRefresh() } );
    },

    /** Render */
    render: function() {
        this.$( '.frame-scroll-up' ) [ this.top != this.options.top_min && 'show' || 'hide' ]();
        this.$( '.frame-scroll-down')[ this.top != this.top_max && 'show' || 'hide' ]();
    },

    /**
     * Adds and displays a new frame.
     *
     * options:
     *  url     : loaded into an iframe
     *  content : content is treated as a function or raw HTML, function is passed a single
     *              argument that is the frame's content DOM element
     */
    add: function( options ) {
        if ( this.frame_counter >= this.options.frame_max ) {
            Galaxy.modal.show( {
                title   : 'Warning',
                body    : 'You have reached the maximum number of allowed frames (' + this.options.frame_max + ').',
                buttons : { 'Close' : function() { Galaxy.modal.hide() } }
            });

        } else {
            var frame_id = '#frame-' + ( this.frame_uid++ );
            if ( $ ( frame_id ).length !== 0 ) {
                Galaxy.modal.show( {
                    title   : 'Error',
                    body    : 'This frame already exists. This page might contain multiple frame managers.',
                    buttons : { 'Close' : function() { Galaxy.modal.hide() } }
                });
            } else {
                // initialize new frame elements
                this.top = this.options.top_min;
                var $frame_el = $( this._frameTemplate( frame_id.substring( 1 ), options.title ) );
                var $frame_content = $frame_el.find( '.f-content' );
                this.$el.append( $frame_el );
                // adds slider icons
                $frame_content.append(                
                	"<a class='f-scroll-left' href='#' data-target-frame=" + frame_id + "> < </a>"
                );
                $frame_content.append(
                	"<a class='f-scroll-right' href='#' data-target-frame=" + frame_id + "> > </a>"
                );
                // configure content
                if ( options.url ) {
                    $frame_content.append(
                        $ ( '<iframe/>' ).addClass( 'f-iframe' )
                                         .attr( 'scrolling', 'auto' )
                                         .attr( 'src', options.url + ( options.url.indexOf( '?' ) === -1 ? '?' : '&' ) + 'widget=True' )
                                         .attr("dataset-id", options.datasetid)
                          );
                } else if ( options.content ) {
                    _.isFunction( options.content ) ? options.content( $frame_content ) : $frame_content.append( options.content );
                    // makes the slider icons visible
                    $(frame_id + ' #content_table').parent().css("position", "");
                    $(frame_id + ' #content_table').attr("dataset-id", options.datasetid);
                }

                // construct a new frame
                var frame = {
                    id              : frame_id,
                    screen_location : {},
                    grid_location   : {},
                    grid_rank       : null,
                    grid_lock       : false
                };

                // set dimensions
                options.width   = this._toPixelCoord( 'width', this.options.frame.cols );
                options.height  = this._toPixelCoord( 'height', this.options.frame.rows );

                // set default z-index and add to ui and frame list
                this.frame_z = parseInt( $( frame.id ).css( 'z-index' ) );
                this.frame_list[ frame_id ] = frame;
                this.frame_counter++;
                this._frameResize( frame, { width: options.width, height: options.height } );
                this._frameInsert( frame, { top: 0, left: 0 }, true );
                !this.visible && this.show();
                this.trigger( 'add' );
            }
        }
    },

    /** Remove a frame */
    del: function( frame_id ) {
        var self = this;
        var $frame = this.$( frame_id );
        $frame.fadeOut( 'fast', function() {
            $frame.remove();
            delete self.frame_list[ frame_id ];
            self.frame_counter--;
            self._panelRefresh( true );
            self._panelAnimationComplete();
            self.trigger( 'remove' );
        });
    },

    /** Show panel */
    show: function() {
        this.visible = true;
        this.$el.fadeIn( 'fast' );
        this.trigger( 'show' );
    },

    /** Hide panel */
    hide: function() {
        if ( !this.event.type ) {
            this.visible = false;
            this.$el.fadeOut('fast', function() { $( this ).hide() });
            this.trigger( 'hide' );
        }
    },

    /** Returns the number of frames */
    length: function() {
        return this.frame_counter;
    },

    /*
        EVENT HANDLING
    */
    events: {
        // global frame events
        'mousemove'                         : '_eventFrameMouseMove',
        'mouseup'                           : '_eventFrameMouseUp',
        'mouseleave'                        : '_eventFrameMouseUp',
        'mousewheel'                        : '_eventPanelScroll',
        'DOMMouseScroll'                    : '_eventPanelScroll',

        // events fixed to elements
        'mousedown .frame'                  : '_eventFrameMouseDown',
        'mousedown .frame-background'       : '_eventHide',
        'mousedown .frame-scroll-up'        : '_eventPanelScroll_up',
        'mousedown .frame-scroll-down'      : '_eventPanelScroll_down',
        'mousedown .f-close'                : '_eventFrameClose',
        'mousedown .f-pin'                  : '_eventFrameLock',
        'mousedown .f-scroll-left'          : '_eventItemScroll_left',
        'mousedown .f-scroll-right'         : '_eventItemScroll_right',
        'mouseenter .f-content'             : '_eventShowItemSlider',
        'mouseleave .f-content'             : '_eventHideItemSlider',
        'mouseenter #content_table'         : '_eventShowItemSlider',
        'mouseleave #content_table'         : '_eventHideItemSlider',
    },

    /** Start drag/resize event */
    _eventFrameMouseDown: function ( e ) {
        if ( !this.event.type ) {
            if ( $( e.target ).hasClass( 'f-header' ) || $( e.target ).hasClass( 'f-title' ) ) {
                this.event.type = 'drag';
            }
            if ( $( e.target ).hasClass( 'f-resize' ) ) {
                this.event.type = 'resize';
            }
            if ( this.event.type ) {
                e.preventDefault();
                this.event.target = this._frameIdentify( e.target );
                if ( this.event.target.grid_lock ) {
                    this.event.type = null;
                    return;
                }
                this.event.xy = {
                    x: e.originalEvent.pageX,
                    y: e.originalEvent.pageY
                };
                this._frameDragStart( this.event.target );
            }
        }
    },

    /** Processes drag/resize events */
    _eventFrameMouseMove: function ( e ) {
        if ( this.event.type ) {
            // get mouse motion and delta
            var event_xy_new = {
                x : e.originalEvent.pageX,
                y : e.originalEvent.pageY
            };
            var event_xy_delta = {
                x : event_xy_new.x - this.event.xy.x,
                y : event_xy_new.y - this.event.xy.y
            };
            this.event.xy = event_xy_new;

            // get current screen position and size of frame
            var p = this._frameScreen ( this.event.target );

            // drag/resize event
            if ( this.event.type == 'resize' ) {
                p.width  += event_xy_delta.x;
                p.height += event_xy_delta.y;
                var min_dim = this.options.cell - this.options.margin - 1;
                p.width = Math.max( p.width, min_dim );
                p.height = Math.max( p.height, min_dim );
                this._frameResize( this.event.target, p );
                p.width = this._toGridCoord( 'width', p.width ) + 1;
                p.height = this._toGridCoord( 'height', p.height ) + 1;
                p.width = this._toPixelCoord( 'width', p.width );
                p.height = this._toPixelCoord( 'height', p.height );
                this._frameResize( this.frame_shadow, p );
                this._frameInsert( this.frame_shadow, {
                    top     : this._toGridCoord( 'top', p.top ),
                    left    : this._toGridCoord( 'left', p.left )
                });
            } else if ( this.event.type == 'drag' ) {
                p.left  += event_xy_delta.x;
                p.top   += event_xy_delta.y;
                this._frameOffset( this.event.target, p );
                var l = {
                    top     : this._toGridCoord( 'top', p.top ),
                    left    : this._toGridCoord( 'left', p.left )
                };
                l.left !== 0 && l.left++;
                this._frameInsert( this.frame_shadow, l );
            }
        }
    },

    /** Stop drag/resize events */
    _eventFrameMouseUp: function ( e ) {
        if ( this.event.type ) {
            this._frameDragStop( this.event.target );
            this.event.type = null;
        }
    },

    /** Destroy a frame */
    _eventFrameClose: function ( e ) {
        if ( !this.event.type ) {
            e.preventDefault();
            this.del( this._frameIdentify( e.target ).id );
        }
    },

    /** Lock/Unlock the frame location */
    _eventFrameLock: function ( e ) {
        if ( !this.event.type ) {
            e.preventDefault();
            var frame = this._frameIdentify( e.target );
            var locked = frame.grid_lock = !frame.grid_lock;
            var $el = $( frame.id );
            $el.find( '.f-pin' )      [ locked && 'addClass' || 'removeClass' ]( 'toggle' );
            $el.find( '.f-header' )   [ locked && 'removeClass' || 'addClass' ]( 'f-not-allowed' );
            $el.find( '.f-title' )    [ locked && 'removeClass' || 'addClass' ]( 'f-not-allowed' );
            $el.find( '.f-resize' )   [ locked && 'hide' || 'show' ]();
            $el.find( '.f-close' )    [ locked && 'hide' || 'show' ]();
        }
    },

    /** Hide all frames */
    _eventHide: function ( e ) {
        !this.event.type && this.hide();
    },

    /** Fired when scrolling occurs on panel */
    _eventPanelScroll: function( e ) {
        if ( !this.event.type && this.visible ) {
            // Stop propagation if scrolling is happening inside a frame.
            // TODO: could propagate scrolling if at top/bottom of frame.
            var frames = $( e.srcElement ).parents( '.frame' );
            if ( frames.length !== 0 ) {
                e.stopPropagation();
            } else {
                e.preventDefault();
                this._panelScroll( e.originalEvent.detail ? e.originalEvent.detail : e.originalEvent.wheelDelta / -3 );
            }
        }
    },

    /** Handle scroll up event */
    _eventPanelScroll_up: function( e ) {
        if ( !this.event.type ) {
            e.preventDefault();
            this._panelScroll( -this.options.scroll );
        }
    },

    /** Handle scroll down */
    _eventPanelScroll_down: function(e) {
        if ( !this.event.type ) {
            e.preventDefault();
            this._panelScroll( this.options.scroll );
        }
    },

    /*
        FRAME EVENTS SUPPORT
    */

    /** Identify the target frame */
    _frameIdentify: function( target ) {
        return this.frame_list[ '#' + $( target ).closest( '.frame' ).attr( 'id' ) ];
    },

    /** Provides drag support */
    _frameDragStart : function ( frame ) {
        this._frameFocus( frame, true );
        var p = this._frameScreen( frame );
        this._frameResize( this.frame_shadow, p );
        this._frameGrid( this.frame_shadow, frame.grid_location );
        frame.grid_location = null;
        $( this.frame_shadow.id ).show();
        $( '.f-cover' ).show();
    },

    /** Removes drag support */
    _frameDragStop : function ( frame ) {
        this._frameFocus( frame, false );
        var p = this._frameScreen( this.frame_shadow );
        this._frameResize( frame, p );
        this._frameGrid( frame, this.frame_shadow.grid_location, true );
        this.frame_shadow.grid_location = null;
        $( this.frame_shadow.id ).hide();
        $( '.f-cover' ).hide();
        this._panelAnimationComplete();
    },

    /*
        GRID/PIXEL CONVERTER
    */

    /** Converts a pixel to a grid dimension */
    _toGridCoord: function ( type, px ) {
        var sign = ( type == 'width' || type == 'height' ) ? 1 : -1;
        type == 'top' && ( px -= this.top );
        return parseInt( ( px + sign * this.options.margin ) / this.options.cell, 10 );
    },
    
    /** Converts a grid to a pixels dimension */
    _toPixelCoord: function ( type, g ) {
        var sign = ( type == 'width' || type == 'height' ) ? 1 : -1;
        var px = ( g * this.options.cell ) - sign * this.options.margin;
        type == 'top' && ( px += this.top );
        return px;
    },

    /** Converts a pixel to a grid coordinate set */
    _toGrid: function ( px ) {
        return {
            top     : this._toGridCoord( 'top', px.top ),
            left    : this._toGridCoord( 'left', px.left ),
            width   : this._toGridCoord( 'width', px.width ),
            height  : this._toGridCoord( 'height', px.height )
        };
    },

    /** Converts a pixel to a grid coordinate set */
    _toPixel: function( g ) {
        return {
            top     : this._toPixelCoord( 'top', g.top ),
            left    : this._toPixelCoord( 'left', g.left ),
            width   : this._toPixelCoord( 'width', g.width ),
            height  : this._toPixelCoord( 'height', g.height )
        };
    },

    /* 
        COLLISION DETECTION
    */

    /** Check collisions for a grid coordinate set */
    _isCollision: function( g ) {
        function is_collision_pair ( a, b ) {
            return !( a.left > b.left + b.width - 1 || a.left + a.width - 1 < b.left ||
                      a.top > b.top + b.height  - 1 || a.top + a.height - 1 < b.top );
        }
        for ( var i in this.frame_list ) {
            var frame = this.frame_list[ i ];
            if ( frame.grid_location !== null && is_collision_pair ( g, frame.grid_location ) ) {
                return true;
            }
        }
        return false;
    },

    /** Return location/grid rank */
    _locationRank: function( loc ) {
        return ( loc.top * this.cols ) + loc.left;
    },

    /*
        PANEL/WINDOW FUNCTIONS
    */

    /** Refresh panel */
    _panelRefresh: function( animate ) {
        this.cols = parseInt( $( window ).width() / this.options.cell, 10 ) + 1;
        this._frameInsert( null, null, animate );
    },

    /** Complete panel animation / frames not moving */
    _panelAnimationComplete: function() {
        var self = this;
        $( '.frame' ).promise().done( function() { self._panelScroll( 0, true ) } );
    },

    /** Scroll panel */
    _panelScroll: function( delta, animate ) {
        var top_new = this.top - this.options.scroll * delta;
        top_new = Math.max( top_new, this.top_max );
        top_new = Math.min( top_new, this.options.top_min );
        if ( this.top != top_new ) {
            for ( var i in this.frame_list ) {
                var frame = this.frame_list[ i ];
                if ( frame.grid_location !== null ) {
                    var screen_location = {
                        top  : frame.screen_location.top - ( this.top - top_new ),
                        left : frame.screen_location.left
                    }
                    this._frameOffset( frame, screen_location, animate );
                }
            }
            this.top = top_new;
        }
        this.render();
    },

    /*
        FRAME FUNCTIONS
    */

    /** Insert frame at given location */
    _frameInsert: function( frame, new_loc, animate ) {
        var self = this;
        var place_list = [];
        if ( frame ) {
            frame.grid_location = null;
            place_list.push( [ frame, this._locationRank( new_loc ) ] );
        }
        _.each( this.frame_list, function( f ) {
            if ( f.grid_location !== null && !f.grid_lock ) {
                f.grid_location = null;
                place_list.push( [ f, f.grid_rank ] );
            }
        });
        place_list.sort( function( a, b ) {
            return a[ 1 ] < b[ 1 ] ? -1 : ( a[ 1 ] > b[ 1 ] ? 1 : 0 );
        });
        _.each( place_list, function( place ) {
            self._framePlace( place[ 0 ], animate );
        });
        this.top_max = 0;
        _.each( this.frame_list, function( f ) {
            if ( f.grid_location !== null ) {
                self.top_max = Math.max( self.top_max, f.grid_location.top + f.grid_location.height );
            }
        });
        this.top_max = $( window ).height() - this.top_max * this.options.cell - 2 * this.options.margin;
        this.top_max = Math.min( this.top_max, this.options.top_min );
        this.render();
    },

    /** Naive frame placement */
    _framePlace: function( frame, animate ) {
        frame.grid_location = null;
        var g = this._toGrid( this._frameScreen( frame ) );
        var done = false;
        for ( var i = 0; i < this.options.rows; i++ ) {
            for ( var j = 0; j < Math.max(1, this.cols - g.width ); j++ ) {
                g.top   = i;
                g.left  = j;
                if ( !this._isCollision( g ) ) {
                    done = true;
                    break;
                }
            }
            if ( done ) {
                break;
            }
        }
        if ( done ) {
            this._frameGrid( frame, g, animate );
        } else {
            console.log( 'Grid dimensions exceeded.' );
        }
    },

    /** Handle frame focussing */
    _frameFocus: function( frame, has_focus ) {
        $( frame.id ).css( 'z-index', this.frame_z + ( has_focus ? 1 : 0 ) );
    },

    /** New left/top position frame */
    _frameOffset: function( frame, p, animate ) {
        frame.screen_location.left = p.left;
        frame.screen_location.top = p.top;
        if ( animate ) {
            this._frameFocus( frame, true );
            var self = this;
            $( frame.id ).animate({ top: p.top, left: p.left }, 'fast', function() {
                self._frameFocus( frame, false );
            });
        } else {
            $( frame.id ).css( { top: p.top, left: p.left } );
        }
    },

    /** Resize frame */
    _frameResize: function( frame, p ) {
        $( frame.id ).css( { width: p.width, height: p.height } );
        frame.screen_location.width = p.width;
        frame.screen_location.height = p.height;
    },

    /** Push frame to new grid location */
    _frameGrid: function ( frame, l, animate ) {
        frame.grid_location = l;
        this._frameOffset( frame, this._toPixel( l ), animate );
        frame.grid_rank = this._locationRank( l );
    },

    /** Get frame dimensions */
    _frameScreen: function( frame ) {
        var p = frame.screen_location;
        return { top: p.top, left: p.left, width: p.width, height: p.height };
    },

    /** Regular frame template */
    _frameTemplate: function( id, title ) {
        return  '<div id="' + id + '" class="frame corner">' +
                    '<div class="f-header corner">' +
                        '<span class="f-title">' + ( title || '' ) + '</span>' +
                        '<span class="f-icon f-close fa fa-close"/>' +
                        '<span class="f-icon f-pin fa fa-thumb-tack"/>' +
                    '</div>' +
                    '<div class="f-content">' +
                        '<div class="f-cover"/>' +
                    '</div>' +
                    '<span class="f-resize f-icon corner fa fa-expand"/>' +
                '</div>';
    },

    /** Slides to previous or next item */
    _slideItem: function( direction, selector, frame_data_attribute, event ) {
        var item_counter = 0,
            all_items = $(selector)[0],
            frame_id = event.srcElement.attributes[frame_data_attribute].value,
            all_items_count = all_items.childElementCount,
            displayed_item_id = null,
            current_item_id = null,
            item_id = null,
            element = null,
            element_id = null,
            item_element = null,
            frame_iframe = $( frame_id + ' iframe' ),
            frame_table = $( frame_id + ' #content_table' );
            
            displayed_item_id = ( !frame_iframe.attr( 'dataset-id' ) ? frame_table.attr( 'dataset-id' ) : 
								       frame_iframe.attr( 'dataset-id' ) );
            // if previous icon ('<') is clicked
            if( direction === 'left' ) {
                item_counter = all_items_count - 1;
                while( item_counter >= 0 ) {
                    item_element = all_items.children[ item_counter ];
                    current_item_id = ( item_element.id ).split('-')[1];
                    // matches the displayed item in the item list
                    if( displayed_item_id === current_item_id ) {
                        // gets the previous element
                        element = ( $(item_element) ).prev();
                        element_id = element.attr( 'id' );
                        if( element_id ) {
                            item_id = element_id.split( '-' )[1];
                            // jQuery fadeOut effect
                            this._jqueryFadeOutEffect( frame_iframe );
                            // fecthes the previous item
                            this._fecthData( item_id, frame_id, element, 'left' );
                            break;
                        }           
                     }
                     item_counter--;
                }
            }
            else {
                // if next icon ('>') is clicked
                while( item_counter < all_items_count ) {
                    item_element = all_items.children[item_counter];
                    current_item_id = ( item_element.id ).split( '-' )[1];
                    // matches the displayed item in the item list
                    if( displayed_item_id === current_item_id ) {
                        // gets the next element
                        element = ( $( item_element ) ).next();
                        element_id = element.attr( 'id' );
                        if( element_id ) {
                            item_id = element_id.split( '-' )[1];
                            // jQuery fadeOut effect
                            this._jqueryFadeOutEffect( frame_iframe );
                            // fecthes the next item
                            this._fecthData( item_id, frame_id, element, 'right' );
                            break;
                        }           
                     }
                     item_counter++;
                }
            }
    },

     /** Jquery Fade out effect */
    _jqueryFadeOutEffect: function(el) {
	if( el.contents().find( 'div' ) ) {
		el.contents().find( 'div' ).fadeOut( 'slow' );
        }
        else if( el.contents().find( 'img' ) ) {
		el.contents().find( 'img' ).fadeOut( 'slow' );
        }
    },

     /** Scrolls to previous item */
    _eventItemScroll_left: function( event ) { 
       var self = this;
       event.stopPropagation();
       self._mergeSlideEvents( 'left', self, event );
    },

     /** Scrolls to next item */
    _eventItemScroll_right: function( event ) {
        var self = this;
        event.stopPropagation();
        self._mergeSlideEvents( 'right', self, event );
    },

    /** Merges the left or right click events on sliders */
    _mergeSlideEvents: function( direction, self, event ) {
 	// clears and sets timeout intervals
        var selector = null;
        if( $( '.list-items' ).css( 'display' ) === "none" ) {
        	selector = $( '.list-panel .list-items' )[1];
        } 
        else {
		selector = ".list-items";
	}
        self._clearsInterval( self.idle_timer );
        self.idle_timer = self._setTimeout( self );
        // slides to previous or next item
        self._slideItem( direction, selector, this.data_target_frame, event );   
    },
   
    /** Fetches the next item */
    _fecthData: function ( dataset_id, frame_id, current_element, direction ) {
        var self = this,
            dataset,
            frame_config;
        require([ 'mvc/dataset/data' ], function( DATA ) {
        	dataset = new DATA.Dataset( { id : dataset_id } );   
            	// fetches the dataset       
            	$.when( dataset.fetch() ).then( function() {
                // Construct frame config based on dataset's type.
                var frame_config = {
                        title: dataset.get( 'name' )
                    },
                    is_tabular = _.find( [ 'tabular', 'interval' ] , function( data_type ) {
                        return dataset.get( 'data_type' ).indexOf( data_type ) !== -1;
                    });

                // Use tabular chunked display if dataset is tabular; otherwise load via URL.
                if ( is_tabular ) {
                    var tabular_dataset = new DATA.TabularDataset( dataset.toJSON() );
                    _.extend( frame_config, {
                        content: function( parent_elt ) {
                            DATA.createTabularDatasetChunkedView({
                                model       : tabular_dataset,
                                parent_elt  : parent_elt,
                                embedded    : true,
                                height      : '100%'
                            });
                        }
                    });
                }
                else {
                    _.extend( frame_config, {
                        url: Galaxy.root + 'datasets/' + dataset.id + '/display/?preview=True',
                        title: dataset.get( 'name' ),
                        data_type: (dataset.get( 'data_type' ).split('.')[3]).toLowerCase()
                    });
                }
                _.extend( frame_config, {
                        datasetid: dataset.id
                    });
                // updates the iframe with new dataset
		self._changeData( frame_config, frame_id, dataset.get( 'data_type' ), current_element, direction );
            });
        });
    },
  
    // Skips some data types
    _skipDatatypes: function( datatype ) {
	// skip_datatypes
        return _.contains( this.skip_datatypes, datatype );
    },
    
    /** Updates iframe with the new item */
    _changeData: function ( options, frame_id, data_type, curr_element, direction ) {
            // loads data into the iframe
            var datatype = data_type.split('.')[3].toLowerCase(),
                is_present = this._skipDatatypes( datatype ),
                element = null,
                element_id = null,
                item_id = null,
                frame_content = $( frame_id + ' .f-content' ),
                frame_content_table = null,
                frame_iframe = $( frame_id + ' iframe' ),
                frame_title = $( frame_id + ' .f-title' );
            // if the datatype is to be skipped from displaying into iframe
            // move to next or previous item
            if( is_present ) {
		if( direction === 'left' ) {
                        // finds the previous element
			element = ( $( curr_element ) ).prev();
                        element_id = element.attr( 'id' );
                        if( element_id ) {
                            item_id = element_id.split( '-' )[1];	
                        }	
		}
                else {
                        // finds the next element
			element = ( $( curr_element ) ).next();
                        element_id = element.attr( 'id' );
                        if( element_id ) {
                            item_id = element_id.split( '-' )[1];
                        }
		}
                // fetches the desired item
                this._fecthData( item_id, frame_id, element, direction );
	    }
            else {
                // updates the data into the iframe or table based on the datatype
                if ( options.url ) {
                        // removes old content
                        this._removeTabularDataDiv( frame_content );
                        // if iframe is there then update its url and datasetid
                        if( frame_iframe ) {
				frame_iframe.attr( 'src', options.url );
                                frame_iframe.attr( 'dataset-id', options.datasetid );
                        }
                        frame_content.append(
				$ ( '<iframe/>' ).addClass( 'f-iframe' )
		                 .attr( 'scrolling', 'auto' )
		                 .attr( 'src', options.url + ( options.url.indexOf( '?' ) === -1 ? '?' : '&' ) + 'widget=True' )
		                 .attr( "dataset-id", options.datasetid )
	        	);
                }
                else if( options.content ) {
                        // removes iframe is present
                        if( frame_iframe ) {
 				$( frame_iframe ).remove();
                        }
                        // removes old content
                        this._removeTabularDataDiv( frame_content );
			// updates the content 
		 	_.isFunction( options.content ) ? options.content( frame_content ) : frame_content.append( options.content );
            		// makes the slider icons visible
                        frame_content_table = $( frame_id + ' #content_table' );
            		frame_content_table.parent().css( "position", "" );
            		frame_content_table.attr( "dataset-id", options.datasetid );
                        
		}
                // updates the title of the frame
                frame_title.text( options.title );
            }
    },

    /** Removes the div of the tabular content */
    _removeTabularDataDiv: function(frame_content) {
	if( frame_content.children()[3] ) {
		$( frame_content.children()[3] ).remove();
        }
    },
     
    /** Fades in the item slider when mouse is over the frame's content */
    _eventShowItemSlider: function( event ) {
        var self = this, 
	    frame_id = $( event.srcElement ).prev().attr( self.data_target_frame );
        // clears and sets timeout intervals
        self._clearsInterval( self.idle_timer );
        self.idle_timer = self._setTimeout( self );
        self._fadeInSlider( frame_id );
        self.idle_counter = 0;
    },
    
    /** Fades out the item slider when mouse leaves the frame content */
     _eventHideItemSlider: function( event ) {
        var self = this,
	    frame_id = $( event.srcElement ).prev().attr( self.data_target_frame ) ;
        self._fadeOutSlider( frame_id );
        self._clearsInterval( self.idle_timer );
        self.idle_counter = 0;
    },
    
    /** Fades out the item slider - jQuery fadeOut*/
    _fadeOutSlider: function( frame_id ) {
        $( frame_id + ' .f-scroll-left' ).fadeOut( 'slow' );
        $( frame_id + ' .f-scroll-right' ).fadeOut( 'slow' );
    },
    
    /** Fades in the item slider - jQuery fadeIn*/
    _fadeInSlider: function( frame_id ) {
        $( frame_id + ' .f-scroll-left' ).fadeIn( 'slow' );
        $( frame_id + ' .f-scroll-right' ).fadeIn( 'slow' );
    },

    /** Increments the counter to when the user is idle */
    _frameIdle: function( this_var ) {
        var self = this_var;
        // increments the idle counter
        self.idle_counter++;
        // checks if the idle counter is greater than a threshold
        if( self.idle_counter > self.idle_interval ) {
                // fades out the sliders and clears timeout interval
                $( '.f-scroll-left' ).fadeOut( 'slow' );
        	$( '.f-scroll-right' ).fadeOut( 'slow' );
                self._clearsInterval( self.idle_timer );
	}
    },

    /** Clear timeout interval */
    _clearsInterval: function( id ) {
        if( id !== null) {
		clearInterval( id );
        }
    },

    /** Sets timeout*/
    _setTimeout: function( self ) {
    	return setInterval( function() { self._frameIdle(self); }, self.interval ); 
    },
});

return {
    View: View
}

});
