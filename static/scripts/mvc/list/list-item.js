define([
    'mvc/base-mvc',
    'utils/localization'
], function( BASE_MVC, _l ){

//==============================================================================
/** A view which, when first rendered, shows only summary data/attributes, but
 *      can be expanded to show further details (and optionally fetch those
 *      details from the server).
 */
var ExpandableView = Backbone.View.extend( BASE_MVC.LoggableMixin ).extend({
//TODO: Although the reasoning behind them is different, this shares a lot with HiddenUntilActivated above: combine them
    //PRECONDITION: model must have method hasDetails
    //PRECONDITION: subclasses must have templates.el and templates.details

    initialize : function( attributes ){
        /** are the details of this view expanded/shown or not? */
        this.expanded   = attributes.expanded || false;
        //this.log( '\t expanded:', this.expanded );
        this.fxSpeed = attributes.fxSpeed || this.fxSpeed;
    },

    // ........................................................................ render main
    /** jq fx speed */
    fxSpeed : 'fast',

    /** Render this content, set up ui.
     *  @param {Number or String} speed   the speed of the render
     */
    render : function( speed ){
        var $newRender = this._buildNewRender();
        this._setUpBehaviors( $newRender );
        this._queueNewRender( $newRender, speed );
        return this;
    },

    /** Build a temp div containing the new children for the view's $el.
     *      If the view is already expanded, build the details as well.
     */
    _buildNewRender : function(){
        // create a new render using a skeleton template, render title buttons, render body, and set up events, etc.
        var $newRender = $( this.templates.el( this.model.toJSON(), this ) );
        if( this.expanded ){
            this.$details( $newRender ).replaceWith( this._renderDetails().show() );
        }
        return $newRender;
    },

    /** Fade out the old el, swap in the new contents, then fade in.
     *  @param {Number or String} speed   jq speed to use for rendering effects
     *  @fires rendered when rendered
     */
    _queueNewRender : function( $newRender, speed ) {
        speed = ( speed === undefined )?( this.fxSpeed ):( speed );
        var view = this;

        $( view ).queue( 'fx', [
            function( next ){ this.$el.fadeOut( speed, next ); },
            function( next ){
                view._swapNewRender( $newRender );
                next();
            },
            function( next ){ this.$el.fadeIn( speed, next ); },
            function( next ){
                this.trigger( 'rendered', view );
                next();
            }
        ]);
    },

    /** empty out the current el, move the $newRender's children in */
    _swapNewRender : function( $newRender ){
        return this.$el.empty().attr( 'class', this.className ).append( $newRender.children() );
    },

    /** set up js behaviors, event handlers for elements within the given container
     *  @param {jQuery} $container jq object that contains the elements to process (defaults to this.$el)
     */
    _setUpBehaviors : function( $where ){
        $where = $where || this.$el;
        // set up canned behavior on children (bootstrap, popupmenus, editable_text, etc.)
        //make_popup_menus( $where );
        $where.find( '[title]' ).tooltip({ placement : 'bottom' });
    },

    // ......................................................................... details
    /** shortcut to details DOM (as jQ) */
    $details : function( $where ){
        $where = $where || this.$el;
        return $where.find( '.details' );
    },

    /** build the DOM for the details and set up behaviors on it */
    _renderDetails : function(){
        var $newDetails = $( this.templates.details( this.model.toJSON(), this ) );
        this._setUpBehaviors( $newDetails );
        return $newDetails;
    },

    // ......................................................................... expansion/details
    /** Show or hide the details
     *  @param {Boolean} expand if true, expand; if false, collapse
     */
    toggleExpanded : function( expand ){
        expand = ( expand === undefined )?( !this.expanded ):( expand );
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
        var view = this;
        return view._fetchModelDetails()
            .always(function(){
                var $newDetails = view._renderDetails();
                view.$details().replaceWith( $newDetails );
                // needs to be set after the above or the slide will not show
                view.expanded = true;
                $newDetails.slideDown( view.fxSpeed, function(){
                    view.trigger( 'expanded', view );
                });
            });
    },

    /** Check for model details and, if none, fetch them.
     *  @returns {jQuery.promise} the model.fetch.xhr if details are being fetched, an empty promise if not
     */
    _fetchModelDetails : function(){
        if( !this.model.hasDetails() ){
            return this.model.fetch();
        }
        return jQuery.when();
    },

    /** Hide the body/details of an HDA.
     *  @fires collapsed when a body has been collapsed
     */
    collapse : function(){
        var view = this;
        view.expanded = false;
        this.$details().slideUp( view.fxSpeed, function(){
            view.trigger( 'collapsed', view );
        });
    }

});


//==============================================================================
/** A view that is displayed in some larger list/grid/collection.
 *      Inherits from Expandable, Selectable, Draggable.
 *  The DOM contains warnings, a title bar, and a series of primary action controls.
 *      Primary actions are meant to be easily accessible item functions (such as delete)
 *      that are rendered in the title bar.
 *
 *  Details are rendered when the user clicks the title bar or presses enter/space when
 *      the title bar is in focus.
 *
 *  Designed as a base class for history panel contents - but usable elsewhere (I hope).
 */
var ListItemView = ExpandableView.extend(
        BASE_MVC.mixin( BASE_MVC.SelectableViewMixin, BASE_MVC.DraggableViewMixin, {

//TODO: that's a little contradictory
    tagName     : 'div',
    className   : 'list-item',

    /** Set up the base class and all mixins */
    initialize : function( attributes ){
        ExpandableView.prototype.initialize.call( this, attributes );
        BASE_MVC.SelectableViewMixin.initialize.call( this, attributes );
        BASE_MVC.DraggableViewMixin.initialize.call( this, attributes );
    },

    // ........................................................................ rendering
    /** In this override, call methods to build warnings, titlebar and primary actions */
    _buildNewRender : function(){
        var $newRender = ExpandableView.prototype._buildNewRender.call( this );
        $newRender.find( '.warnings' ).replaceWith( this._renderWarnings() );
        $newRender.find( '.title-bar' ).replaceWith( this._renderTitleBar() );
        $newRender.find( '.primary-actions' ).append( this._renderPrimaryActions() );
        $newRender.find( '.subtitle' ).replaceWith( this._renderSubtitle() );
        return $newRender;
    },

    /** In this override, render the selector controls and set up dragging before the swap */
    _swapNewRender : function( $newRender ){
        ExpandableView.prototype._swapNewRender.call( this, $newRender );
        if( this.selectable ){ this.showSelector( 0 ); }
        if( this.draggable ){ this.draggableOn(); }
        return this.$el;
    },

    /** Render any warnings the item may need to show (e.g. "I'm deleted") */
    _renderWarnings : function(){
        var view = this,
            $warnings = $( '<div class="warnings"></div>' ),
            json = view.model.toJSON();
//TODO:! unordered (map)
        _.each( view.templates.warnings, function( templateFn ){
            $warnings.append( $( templateFn( json, view ) ) );
        });
        return $warnings;
    },

    /** Render the title bar (the main/exposed SUMMARY dom element) */
    _renderTitleBar : function(){
        return $( this.templates.titleBar( this.model.toJSON(), this ) );
    },

    /** Return an array of jQ objects containing common/easily-accessible item controls */
    _renderPrimaryActions : function(){
        // override this
        return [];
    },

    /** Render the title bar (the main/exposed SUMMARY dom element) */
    _renderSubtitle : function(){
        return $( this.templates.subtitle( this.model.toJSON(), this ) );
    },

    // ......................................................................... events
    /** event map */
    events : {
        // expand the body when the title is clicked or when in focus and space or enter is pressed
        'click .title-bar'      : '_clickTitleBar',
        'keydown .title-bar'    : '_keyDownTitleBar',

        // dragging - don't work, originalEvent === null
        //'dragstart .dataset-title-bar'  : 'dragStartHandler',
        //'dragend .dataset-title-bar'    : 'dragEndHandler'

        'click .selector'       : 'toggleSelect'
    },

    /** expand when the title bar is clicked */
    _clickTitleBar : function( event ){
        event.stopPropagation();
        this.toggleExpanded();
    },

    /** expand when the title bar is in focus and enter or space is pressed */
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
    },

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'ListItemView(' + modelString + ')';
    }
}));

// ............................................................................ TEMPLATES
/** underscore templates */
ListItemView.prototype.templates = (function(){
//TODO: move to require text! plugin

    var elTemplato = BASE_MVC.wrapTemplate([
        '<div class="list-element">',
            // errors, messages, etc.
            '<div class="warnings"></div>',

            // multi-select checkbox
            '<div class="selector">',
                '<span class="fa fa-2x fa-square-o"></span>',
            '</div>',
            // space for title bar buttons - gen. floated to the right
            '<div class="primary-actions"></div>',
            '<div class="title-bar"></div>',

            // expandable area for more details
            '<div class="details"></div>',
        '</div>'
    ]);

    var warnings = {};

    var titleBarTemplate = BASE_MVC.wrapTemplate([
        // adding a tabindex here allows focusing the title bar and the use of keydown to expand the dataset display
        '<div class="title-bar clear" tabindex="0">',
//TODO: prob. belongs in dataset-list-item
            '<span class="state-icon"></span>',
            '<div class="title">',
                '<span class="name"><%- element.name %></span>',
            '</div>',
            '<div class="subtitle"></div>',
        '</div>'
    ], 'element' );

    var subtitleTemplate = BASE_MVC.wrapTemplate([
        // override this
        '<div class="subtitle"></div>'
    ]);

    var detailsTemplate = BASE_MVC.wrapTemplate([
        // override this
        '<div class="details"></div>'
    ]);

    return {
        el          : elTemplato,
        warnings    : warnings,
        titleBar    : titleBarTemplate,
        subtitle    : subtitleTemplate,
        details     : detailsTemplate
    };
}());


//==============================================================================
    return {
        ExpandableView                  : ExpandableView,
        ListItemView                    : ListItemView
    };
});
