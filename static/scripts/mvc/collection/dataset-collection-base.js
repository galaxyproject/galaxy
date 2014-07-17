define([
    "mvc/history/history-content-base-view",
    "utils/localization"
], function( historyContentBaseView, _l ){
/* global Backbone, LoggableMixin */
//==============================================================================
/** @class Read only view for HistoryDatasetCollectionAssociation.
 *  @name HDABaseView
 *
 *  @augments Backbone.View
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var DatasetCollectionBaseView = historyContentBaseView.HistoryContentBaseView.extend({
    className   : "dataset hda history-panel-hda",
    id          : function(){ return 'hdca-' + this.model.get( 'id' ); },

    /**  */
    initialize  : function( attributes ){
        if( attributes.logger ){ this.logger = this.model.logger = attributes.logger; }
        this.log( this + '.initialize:', attributes );
        /** is the view currently in selection mode? */
        this.selectable = attributes.selectable || false;
        //this.log( '\t selectable:', this.selectable );
        /** is the view currently selected? */
        this.selected   = attributes.selected || false;
        /** is the body of this collection view expanded/not? */
        this.expanded   = attributes.expanded || false;
    },

    /** */
    render : function( fade ){
        var $newRender = this._buildNewRender();

        this._queueNewRender( $newRender, fade );
        return this;
    },

    /** */
    _buildNewRender : function(){
        var $newRender = $( DatasetCollectionBaseView.templates.skeleton( this.model.toJSON() ) );
        $newRender.find( '.dataset-primary-actions' ).append( this._render_titleButtons() );
        $newRender.children( '.dataset-body' ).replaceWith( this._render_body() );
        this._setUpBehaviors( $newRender );
        return $newRender;
    },

    /** */
    _queueNewRender : function( $newRender, fade ) {
        fade = ( fade === undefined )?( true ):( fade );
        var view = this;

        // fade the old render out (if desired)
        if( fade ){
            $( view ).queue( function( next ){ this.$el.fadeOut( view.fxSpeed, next ); });
        }
        // empty the old render, update to any new HDA state, swap in the new render contents, handle multi-select
        $( view ).queue( function( next ){
            this.$el.empty()
                .attr( 'class', view.className ).addClass( 'state-' + view.model.get( 'state' ) )
                .append( $newRender.children() );
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
            if( this.model.inReadyState() ){
                this.trigger( 'rendered:ready', view );
            }
            if( this.draggable ){ this.draggableOn(); }
            next();
        });
    },

    // ................................................................................ titlebar buttons
    /** Render icon-button group for the common, most easily accessed actions.
     *  @returns {jQuery} rendered DOM
     */
    _render_titleButtons : function(){
        // render just the display for read-only
        return [ ];
    },

    // ......................................................................... state body renderers
    /** Render the enclosing div of the collection body and, if expanded, the html in the body
     *  @returns {jQuery} rendered DOM
     */
    _render_body : function(){
        var $body = $( '<div>Error: unknown state "' + this.model.get( 'state' ) + '".</div>' ),
            // cheesy: get function by assumed matching name
            renderFn = this[ '_render_body_' + this.model.get( 'state' ) ];
        if( _.isFunction( renderFn ) ){
            $body = renderFn.call( this );
        }
        this._setUpBehaviors( $body );

        // only render the body html if it's being shown
        if( this.expanded ){
            $body.show();
        }
        return $body;
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

    // TODO: Eliminate duplication between following event map and one for HDAs.

    // ......................................................................... events
    /** event map */
    events : {
        // expand the body when the title is clicked or when in focus and space or enter is pressed
        'click .dataset-title-bar'      : 'toggleBodyVisibility',
        'keydown .dataset-title-bar'    : 'toggleBodyVisibility',

        // toggle selected state
        'click .dataset-selector'       : 'toggleSelect'
    },

    /** Show or hide the body/details of history content.
     *      note: if the model does not have detailed data, fetch that data before showing the body
     *  @param {Event} event the event that triggered this (@link HDABaseView#events)
     *  @param {Boolean} expanded if true, expand; if false, collapse
     *  @fires body-expanded when a body has been expanded
     *  @fires body-collapsed when a body has been collapsed
     */
    toggleBodyVisibility : function( event, expand ){
        // bail (with propagation) if keydown and not space or enter
        var KEYCODE_SPACE = 32, KEYCODE_RETURN = 13;
        if( event && ( event.type === 'keydown' )
        &&  !( event.keyCode === KEYCODE_SPACE || event.keyCode === KEYCODE_RETURN ) ){
            return true;
        }

        var $body = this.$el.find( '.dataset-body' );
        expand = ( expand === undefined )?( !$body.is( ':visible' ) ):( expand );
        if( expand ){
            this.expandBody();
        } else {
            this.collapseBody();
        }
        return false;
    },

    /** Render and show the full, detailed body of this view including extra data and controls.
     *  @fires body-expanded when a body has been expanded
     */
    expandBody : function(){
        var contentView = this;

        function _renderBodyAndExpand(){
            contentView.$el.children( '.dataset-body' ).replaceWith( contentView._render_body() );
            contentView.$el.children( '.dataset-body' ).slideDown( contentView.fxSpeed, function(){
                    contentView.expanded = true;
                    contentView.trigger( 'body-expanded', contentView.model );
                });
        }
        // TODO: Fetch more details like HDA view...
        _renderBodyAndExpand();
    },

    /** Hide the body/details of an HDA.
     *  @fires body-collapsed when a body has been collapsed
     */
    collapseBody : function(){
        var hdaView = this;
        this.$el.children( '.dataset-body' ).slideUp( hdaView.fxSpeed, function(){
            hdaView.expanded = false;
            hdaView.trigger( 'body-collapsed', hdaView.model.id );
        });
    },

    /** Render an 'ok' collection.
     *  @param {jQuery} parent DOM to which to append this body
     */
    _render_body_ok : function(){
        // most common state renderer and the most complicated
        var $body = $( DatasetCollectionBaseView.templates.body( this.model.toJSON() ) );

        // return shortened form if del'd (no display apps or peek?)
        if( this.model.get( 'deleted' ) ){
            return $body;
        }

        return $body;
    },
    
    // ......................................................................... selection
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

    toggleSelector : function(){
        if( !this.$el.find( '.dataset-selector' ).is( ':visible' ) ){
            this.showSelector();
        } else {
            this.hideSelector();
        }
    },

    /** event handler for selection (also programmatic selection)
     */
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

    /** event handler for clearing selection (also programmatic deselection)
     */
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

    toggleSelect : function( event ){
        if( this.selected ){
            this.deselect( event );
        } else {
            this.select( event );
        }
    },

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'HDCABaseView(' + modelString + ')';
    }
});

//------------------------------------------------------------------------------ TEMPLATES
//TODO: possibly break these out into a sep. module
var skeletonTemplate = _.template([
    '<div class="dataset hda">',
        '<div class="dataset-warnings">',
            '<% if ( collection.deleted ) { %>',
                '<div class="dataset-deleted-msg warningmessagesmall"><strong>',
                    _l( 'This collection has been deleted.' ),
                '</div>',
            '<% } %>',
            '<% if ( !collection.visible ) { %>',
                '<div class="dataset-hidden-msg warningmessagesmall"><strong>',
                    _l( 'This collection has been hidden.' ),
                '</div>',
            '<% } %>',
        '</div>',
        '<div class="dataset-selector"><span class="fa fa-2x fa-square-o"></span></div>',
        '<div class="dataset-primary-actions"></div>',
        '<div class="dataset-title-bar clear" tabindex="0">',
            '<span class="dataset-state-icon state-icon"></span>',
            '<div class="dataset-title">',
                '<span class="hda-hid"><%= collection.hid %></span> ',
                '<span class="dataset-name"><%= collection.name %></span>',
            '</div>',
        '</div>',
        '<div class="dataset-body"></div>',
    '</div>'
].join( '' ));

var bodyTemplate = _.template([
    '<div class="dataset-body">',
        '<div class="dataset-summary">',
        _l( 'A dataset collection.' ),
    '</div>'
].join( '' ));

DatasetCollectionBaseView.templates = {
    // we override here in order to pass the localizer (_L) into the template scope - since we use it as a fn within
    skeleton            : function( collectionJSON ){
        return skeletonTemplate({ _l: _l, collection: collectionJSON });
    },
    body                : function( collectionJSON ){
        return bodyTemplate({ _l: _l, collection: collectionJSON });
    }
};

//==============================================================================
    return {
        DatasetCollectionBaseView : DatasetCollectionBaseView
    };
});
