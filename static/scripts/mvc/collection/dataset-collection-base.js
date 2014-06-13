define([
    "mvc/dataset/hda-model",
    "mvc/dataset/hda-base"
], function( hdaModel, hdaBase ){
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
var DatasetCollectionBaseView = hdaBase.HistoryContentBaseView.extend({
    className   : "dataset hda history-panel-hda",
    id          : function(){ return 'hdca-' + this.model.get( 'id' ); },

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

    render : function( fade ){
        var $newRender = this._buildNewRender();

        this._queueNewRender( $newRender, fade );
        return this;
    },

    // main template for folder browsing
    templateSkeleton : function (){
        return [
            '<div class="dataset hda">',
                '<div class="dataset-warnings">',
                    '<% if ( deleted ) { %>',
                        '<div class="dataset-deleted-msg warningmessagesmall"><strong>',
                            _l( 'This dataset has been deleted.' ),
                        '</div>',
                    '<% } %>',
                    '<% if ( ! visible ) { %>',
                        '<div class="dataset-hidden-msg warningmessagesmall"><strong>',
                            _l( 'This dataset has been hidden.' ),
                        '</div>',
                    '<% } %>',
                '</div>',
                '<div class="dataset-selector"><span class="fa fa-2x fa-square-o"></span></div>',
                '<div class="dataset-primary-actions"></div>',
                '<div class="dataset-title-bar clear" tabindex="0">',
                    '<span class="dataset-state-icon state-icon"></span>',
                    '<div class="dataset-title">',
                        '<span class="hda-hid"><%= hid %></span> ',
                        '<span class="dataset-name"><%= name %></span>',
                    '</div>',
                '</div>',
                '<div class="dataset-body"></div>',
            '</div>'
        ].join( '' );
    },

    templateBody : function() {
        return [
            '<div class="dataset-body">',
                '<div class="dataset-summary">',
                'A dataset collection.',
            '</div>'
        ].join( '' );
    },
    
    _buildNewRender : function(){
        var $newRender = $( _.template(this.templateSkeleton(), this.model.toJSON() ) );
        $newRender.find( '.dataset-primary-actions' ).append( this._render_titleButtons() );
        $newRender.children( '.dataset-body' ).replaceWith( this._render_body() );
        this._setUpBehaviors( $newRender );
        return $newRender;
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
        var $body = $( _.template( this.templateBody(), this.model.toJSON() ) );

        // return shortened form if del'd (no display apps or peek?)
        if( this.model.get( 'deleted' ) ){
            return $body;
        }

        return $body;
    }
    
});

//==============================================================================
return {
    DatasetCollectionBaseView : DatasetCollectionBaseView
};

});
