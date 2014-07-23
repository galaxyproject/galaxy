define([
    "mvc/base-mvc",
    "utils/localization"
], function( BASE_MVC, _l ){
/* global Backbone */
//==============================================================================
/** @class Read only view for history content views to mixin/extend.
 *      Functionality here should be history-centric.
 */
var HistoryContentViewMixin = {

//TODO: most of the fns/attrs here are basal to any sort of list view - consider moving
    initialize : function( attributes ){
        this.debug( 'HistoryContentViewMixin', attributes );
        //NOTE: it's assumed that this will be mixed into models that have extended LoggableMixin
        //  and calling log/debug/metric will be copasetic

        /** is the view currently in selection mode? */
        this.selectable = attributes.selectable || false;
        this.log( '\t selectable:', this.selectable );
        /** is the view currently selected? */
        this.selected   = attributes.selected || false;
        this.log( '\t selected:', this.selected );
        /** is the body of this view expanded/not? */
        this.expanded   = attributes.expanded || false;
        this.log( '\t expanded:', this.expanded );
    },

    // ........................................................................ render main
    /** Render this content, set up ui.
     *  @param {Boolean} fade   whether or not to fade out/in when re-rendering
     *  @fires rendered when rendered
     *  @fires rendered:ready when first rendered and NO running HDAs
     *  @returns {Object} this HDABaseView
     */
    render : function( fade ){
        var $newRender = this._buildNewRender();
        this._queueNewRender( $newRender, fade );
        return this;
    },

    _buildNewRender : function(){
        // create a new render using a skeleton template, render title buttons, render body, and set up events, etc.
        var $newRender = $( this.templates.skeleton( this.model.toJSON() ) );
        var titleButtons = this._render_titleButtons();
        $newRender.find( '.dataset-primary-actions' ).append( this._render_titleButtons() );
        $newRender.children( '.dataset-body' ).replaceWith( this._renderBody() );
        this._setUpBehaviors( $newRender );
        //this._renderSelectable( $newRender );
        return $newRender;
    },

    /** Fade out the old el, replace with new dom, then fade in.
     *  @param {Boolean} fade   whether or not to fade out/in when re-rendering
     *  @fires rendered when rendered
     *  @fires rendered:ready when first rendered and NO running HDAs
     */
    _queueNewRender : function( $newRender, fade ) {
        fade = ( fade === undefined )?( true ):( fade );
        var view = this;

        // fade the old render out (if desired)
        if( fade ){
            $( view ).queue( function( next ){ this.$el.fadeOut( view.fxSpeed, next ); });
        }
        // empty the old render, update to any new HDA state, swap in the new render contents, handle multi-select
        $( view ).queue( function( next ){
//TODO:?? change to replaceWith pattern?
            this.$el.empty().attr( 'class', view.className ).append( $newRender.children() );
            if( this.model.has( 'state' ) ){
                this.$el.addClass( 'state-' + view.model.get( 'state' ) );
            }
            if( this.selectable ){ this.showSelector( 0 ); }
            next();
        });
        // fade the new in
        if( fade ){
            $( view ).queue( function( next ){ this.$el.fadeIn( view.fxSpeed, next ); });
        }
        // trigger an event to know we're ready
        $( view ).queue( function( next ){
            this.trigger( 'rendered', view );
//TODO: move to echo (listen for rendered, check state, fire rendered:ready)
            if( this.model.inReadyState() ){
                this.trigger( 'rendered:ready', view );
            }
            if( this.draggable ){ this.draggableOn(); }
            next();
        });
    },

    /** set up js behaviors, event handlers for elements within the given container
     *  @param {jQuery} $container jq object that contains the elements to process (defaults to this.$el)
     */
    _setUpBehaviors : function( $container ){
        $container = $container || this.$el;
        // set up canned behavior on children (bootstrap, popupmenus, editable_text, etc.)
        make_popup_menus( $container );
        $container.find( '[title]' ).tooltip({ placement : 'bottom' });
    },

    // ........................................................................ titlebar buttons
    /** Render icon-button group for the common, most easily accessed actions.
     *  @returns {jQuery} rendered DOM or null
     */
    _render_titleButtons : function(){
        // override
        return [];
    },

    // ......................................................................... details
    _renderBody : function(){
        // override this
        return null;
    },

    // ......................................................................... expansion/details
    /** Show or hide the body/details of history content.
     *  @param {Boolean} expand if true, expand; if false, collapse
     */
    toggleExpanded : function( expand ){
        expand = ( expand === undefined )?( !this.expanded ):( expand );
        this.warn( this + '.toggleExpanded, expand:', expand );
        if( expand ){
            this.expand();
        } else {
            this.collapse();
        }
        return this;
    },

    /** Render and show the full, detailed body of this view including extra data and controls.
     *      note: if the model does not have detailed data, fetch that data before showing the body
     *  @fires expanded when a body has been expanded
     */
    expand : function(){
        this.warn( this + '.expand' );
        var contentView = this;

        function _renderBodyAndExpand(){
            contentView.$el.children( '.dataset-body' ).replaceWith( contentView._renderBody() );
            // needs to be set after the above or the slide will not show
            contentView.expanded = true;
            contentView.$el.children( '.dataset-body' ).slideDown( contentView.fxSpeed, function(){
                    contentView.trigger( 'expanded', contentView.model );
                });
        }
        // fetch first if no details in the model
        if( this.model.inReadyState() && !this.model.hasDetails() ){
            // we need the change event on HDCA's for the elements to be processed - so silent == false
            this.model.fetch().always( function( model ){
                _renderBodyAndExpand();
            });
        } else {
            _renderBodyAndExpand();
        }
    },

    /** Hide the body/details of an HDA.
     *  @fires collapsed when a body has been collapsed
     */
    collapse : function(){
        var contentView = this;
        contentView.expanded = false;
        this.$el.children( '.dataset-body' ).slideUp( contentView.fxSpeed, function(){
            contentView.trigger( 'collapsed', contentView.model.id );
        });
    },

    // ......................................................................... selection
//TODO: to more generic view mixin: Selectable (or some other crappy name)
    /** display a (fa-icon) checkbox on the left of the hda that fires events when checked
     *      Note: this also hides the primary actions
     */
    showSelector : function(){
        // make sure selected state is represented properly
        if( this.selected ){
            this.select( null, true );
        }

        this.selectable = true;
        this.trigger( 'selectable', true, this );

        this.$( '.dataset-primary-actions' ).hide();
        this.$( '.dataset-selector' ).show();
    },

    /** remove the selection checkbox */
    hideSelector : function(){
        // reverse the process from showSelect
        this.selectable = false;
        this.trigger( 'selectable', false, this );

        this.$( '.dataset-selector' ).hide();
        this.$( '.dataset-primary-actions' ).show();
    },

    /**  */
    toggleSelector : function(){
        if( !this.$el.find( '.dataset-selector' ).is( ':visible' ) ){
            this.showSelector();
        } else {
            this.hideSelector();
        }
    },

    /** event handler for selection (also programmatic selection) */
    select : function( event ){
        // switch icon, set selected, and trigger event
        this.$el.find( '.dataset-selector span' )
            .removeClass( 'fa-square-o' ).addClass( 'fa-check-square-o' );
        if( !this.selected ){
            this.trigger( 'selected', this, event );
            this.selected = true;
        }
        return false;
    },

    /** event handler for clearing selection (also programmatic deselection) */
    deselect : function( event ){
        // switch icon, set selected, and trigger event
        this.$el.find( '.dataset-selector span' )
            .removeClass( 'fa-check-square-o' ).addClass( 'fa-square-o' );
        if( this.selected ){
            this.trigger( 'de-selected', this, event );
            this.selected = false;
        }
        return false;
    },

    /**  */
    toggleSelect : function( event ){
        if( this.selected ){
            this.deselect( event );
        } else {
            this.select( event );
        }
    },

    // ......................................................................... drag/drop
//TODO: to more generic view mixin: draggable
    /**  */
    draggableOn : function(){
        this.draggable = true;
        //TODO: I have no idea why this doesn't work with the events hash or jq.on()...
        //this.$el.find( '.dataset-title-bar' )
        //    .attr( 'draggable', true )
        //    .bind( 'dragstart', this.dragStartHandler, false )
        //    .bind( 'dragend',   this.dragEndHandler,   false );
        this.dragStartHandler = _.bind( this._dragStartHandler, this );
        this.dragEndHandler   = _.bind( this._dragEndHandler,   this );

        var titleBar = this.$el.find( '.dataset-title-bar' ).attr( 'draggable', true ).get(0);
        titleBar.addEventListener( 'dragstart', this.dragStartHandler, false );
        titleBar.addEventListener( 'dragend',   this.dragEndHandler,   false );
    },

    /**  */
    draggableOff : function(){
        this.draggable = false;
        var titleBar = this.$el.find( '.dataset-title-bar' ).attr( 'draggable', false ).get(0);
        titleBar.removeEventListener( 'dragstart', this.dragStartHandler, false );
        titleBar.removeEventListener( 'dragend',   this.dragEndHandler,   false );
    },

    /**  */
    toggleDraggable : function(){
        if( this.draggable ){
            this.draggableOff();
        } else {
            this.draggableOn();
        }
    },

    /**  */
    _dragStartHandler : function( event ){
        //console.debug( 'dragStartHandler:', this, event, arguments )
        this.trigger( 'dragstart', this );
        event.dataTransfer.effectAllowed = 'move';
        //TODO: all except IE: should be 'application/json', IE: must be 'text'
        event.dataTransfer.setData( 'text', JSON.stringify( this.model.toJSON() ) );
        return false;
    },

    /**  */
    _dragEndHandler : function( event ){
        this.trigger( 'dragend', this );
        //console.debug( 'dragEndHandler:', event )
        return false;
    },

    // ......................................................................... events
    events : {
        // expand the body when the title is clicked or when in focus and space or enter is pressed
        'click .dataset-title-bar'      : '_clickTitleBar',
        'keydown .dataset-title-bar'    : '_keyDownTitleBar',

        // dragging - don't work, originalEvent === null
        //'dragstart .dataset-title-bar'  : 'dragStartHandler',
        //'dragend .dataset-title-bar'    : 'dragEndHandler'

        'click .dataset-selector'       : 'toggleSelect'
    },

    _clickTitleBar : function( event ){
        event.stopPropagation();
        this.toggleExpanded();
    },

    _keyDownTitleBar : function( event ){
        // bail (with propagation) if keydown and not space or enter
        var KEYCODE_SPACE = 32, KEYCODE_RETURN = 13;
        if( event && ( event.type === 'keydown' )
        &&( event.keyCode === KEYCODE_SPACE || event.keyCode === KEYCODE_RETURN ) ){
            this.toggleExpanded();
            event.stopPropagation();
            return false;
        }
        return true;
    }
};

//NOTE: no templates, they're defined at the leaves of the hierarchy
//TODO:?? you sure about that?

//==============================================================================
/** @class Read only view for history content views to extend.
 *  @name HistoryContentBaseView
 *
 *  @augments Backbone.View
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HistoryContentBaseView = Backbone.View.extend( BASE_MVC.LoggableMixin ).extend(
/** @lends HistoryContentBaseView.prototype */HistoryContentViewMixin );

//TODO: not sure base view class is warranted or even wise

//==============================================================================
    return {
        HistoryContentViewMixin : HistoryContentViewMixin,
        HistoryContentBaseView  : HistoryContentBaseView
    };
});
