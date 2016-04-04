define([
    'jquery',
    'libs/underscore',
    'libs/backbone',
    'mvc/base-mvc',
], function( jQuery, _, Backbone, BASE_MVC ){

"use strict";
// ============================================================================
var $ = jQuery;

var MIN_PANEL_WIDTH = 160,
    MAX_PANEL_WIDTH = 800;

// ----------------------------------------------------------------------------
/**
 *
 */
var SidePanel = Backbone.View.extend( BASE_MVC.LoggableMixin ).extend({
    _logNamespace : 'layout',

    initialize: function( attributes ){
        this.log( this + '.initialize:', attributes );
        this.title = attributes.title || this.title || '';

        this.hidden = false;
        this.savedSize = null;
        this.hiddenByTool = false;
    },

    $center : function(){
        return this.$el.siblings( '#center' );
    },

    $toggleButton : function(){
        return this.$( '.unified-panel-footer > .panel-collapse' );
    },

    render: function(){
        this.log( this + '.render:' );
        this.$el.html( this.template( this.id ) );
    },

    /** panel dom template. id is 'right' or 'left' */
    template: function(){
        return [
            this._templateHeader(),
            this._templateBody(),
            this._templateFooter(),
        ].join('');
    },

    /** panel dom template. id is 'right' or 'left' */
    _templateHeader: function( data ){
        return [
            '<div class="unified-panel-header" unselectable="on">',
                '<div class="unified-panel-header-inner">',
                    '<div class="panel-header-buttons" style="float: right"/>',
                    '<div class="panel-header-text">', _.escape( this.title ), '</div>',
                '</div>',
            '</div>',
        ].join('');
    },

    /** panel dom template. id is 'right' or 'left' */
    _templateBody: function( data ){
        return '<div class="unified-panel-body"/>';
    },

    /** panel dom template. id is 'right' or 'left' */
    _templateFooter: function( data ){
        return [
            '<div class="unified-panel-footer">',
                '<div class="panel-collapse ', _.escape( this.id ), '"/>',
                '<div class="drag"/>',
            '</div>',
        ].join('');
    },

    // ..............................................................
    events : {
        'mousedown .unified-panel-footer > .drag'       : '_mousedownDragHandler',
        'click .unified-panel-footer > .panel-collapse' : 'toggle'
    },

    _mousedownDragHandler : function( ev ){
        var self = this,
            draggingLeft = this.id === 'left',
            prevX = ev.pageX;

        function move( e ){
            var delta = e.pageX - prevX;
            prevX = e.pageX;

            var oldWidth = self.$el.width(),
                newWidth = draggingLeft?( oldWidth + delta ):( oldWidth - delta );
            // Limit range
            newWidth = Math.min( MAX_PANEL_WIDTH, Math.max( MIN_PANEL_WIDTH, newWidth ) );
            self.resize( newWidth );
        }

        // this is a page wide overlay that assists in capturing the move and release of the mouse
        // if not provided, progress and end wouldn't fire if the mouse moved out of the drag button area
        $( '#dd-helper' )
            .show()
            .on( 'mousemove', move )
            .one( 'mouseup', function( e ){
                $( this ).hide().off( 'mousemove', move );
            });
    },

    //TODO: the following three could be simplified I think
    resize : function( newSize ){
        this.$el.css( 'width', newSize );
        // if panel is 'right' (this.id), move center right newSize number of pixels
        this.$center().css( this.id, newSize );
        return self;
    },

    show : function(){
        if( !this.hidden ){ return; }
        var self = this,
            animation = {},
            whichSide = this.id;

        animation[ whichSide ] = 0;
        self.$el
            .css( whichSide, -this.savedSize )
            .show()
            .animate( animation, "fast", function(){
                self.resize( self.savedSize );
            });

        self.hidden = false;
        self.$toggleButton().removeClass( "hidden" );
        return self;
    },

    hide : function(){
        if( this.hidden ){ return; }
        var self = this,
            animation = {},
            whichSide = this.id;

        self.savedSize = this.$el.width();
        animation[ whichSide ] = -this.savedSize;
        this.$el.animate( animation, "fast" );
        this.$center().css( whichSide, 0 );

        self.hidden = true;
        self.$toggleButton().addClass( "hidden" );
        return self;
    },

    toggle: function( ev ){
        var self = this;
        if( self.hidden ){
            self.show();
        } else {
            self.hide();
        }
        self.hiddenByTool = false;
        return self;
    },

    // ..............................................................
    //TODO: only used in message.mako?
    /**   */
    handle_minwidth_hint: function( hint ){
        var space = this.$center().width() - ( this.hidden ? this.savedSize : 0 );
        if( space < hint ){
            if( !this.hidden ){
                this.toggle();
                this.hiddenByTool = true;
            }
        } else {
            if( this.hiddenByTool ){
                this.toggle();
                this.hiddenByTool = false;
            }
        }
        return self;
    },

    /**   */
    force_panel : function( op ){
        if( op == 'show' ){ return this.show(); }
        if( op == 'hide' ){ return this.hide(); }
        return self;
    },

    toString : function(){ return 'SidePanel(' + this.id + ')'; }
});

// ----------------------------------------------------------------------------
// TODO: side should be defined by page - not here
var LeftPanel = SidePanel.extend({
    id : 'left',
});

var RightPanel = SidePanel.extend({
    id : 'right',
});


// ----------------------------------------------------------------------------
/**
 *
 */
var CenterPanel = Backbone.View.extend( BASE_MVC.LoggableMixin ).extend({
    _logNamespace : 'layout',

    initialize : function( options ){
        this.log( this + '.initialize:', options );
        /** previous view contained in the center panel - cached for removal later */
        this.prev = null;
    },

    render : function(){
        this.log( this + '.render:' );
        this.$el.html( this.template() );
        // ?: doesn't work/listen in events map
        this.$( '#galaxy_main' ).on( 'load', _.bind( this._iframeChangeHandler, this ) );
    },

    /**   */
    _iframeChangeHandler : function( ev ){
        var iframe = ev.currentTarget;
        var location = iframe.contentWindow && iframe.contentWindow.location;
        if( location && location.host ){
            // show the iframe and hide MVCview div, remove any views in the MVCview div
            $( iframe ).show();
            if( this.prev ){
                this.prev.remove();
            }
            this.$( '#center-panel' ).hide();
            // TODO: move to Galaxy
            Galaxy.trigger( 'galaxy_main:load', {
                fullpath: location.pathname + location.search + location.hash,
                pathname: location.pathname,
                search  : location.search,
                hash    : location.hash
            });
        }
    },

    /**   */
    display: function( view ){
        // we need to display an MVC view: hide the iframe and show the other center panel
        // first checking for any onbeforeunload handlers on the iframe
        var contentWindow = this.$( '#galaxy_main' )[ 0 ].contentWindow || {};
        var message = contentWindow.onbeforeunload && contentWindow.onbeforeunload();
        if ( !message || confirm( message ) ) {
            contentWindow.onbeforeunload = undefined;
            // remove any previous views
            if( this.prev ){
                this.prev.remove();
            }
            this.prev = view;
            this.$( '#galaxy_main' ).attr( 'src', 'about:blank' ).hide();
            this.$( '#center-panel' ).scrollTop( 0 ).append( view.$el ).show();
            Galaxy.trigger( 'center-panel:load', view );

        } else {
            if( view ){
                view.remove();
            }
        }
    },

    template: function(){
        return [
            //TODO: remove inline styling
            '<div style="position: absolute; width: 100%; height: 100%">',
                '<iframe name="galaxy_main" id="galaxy_main" frameborder="0" ',
                        'style="position: absolute; width: 100%; height: 100%;"/>',
                '<div id="center-panel" ',
                     'style="display: none; position: absolute; width: 100%; height: 100%; padding: 10px; overflow: auto;"/>',
            '</div>'
        ].join('');
    },

    toString : function(){ return 'CenterPanel'; }
});


// ============================================================================
    return {
        LeftPanel : LeftPanel,
        RightPanel : RightPanel,
        CenterPanel : CenterPanel
    };
});
