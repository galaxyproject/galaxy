define([
    "mvc/base-mvc",
    "utils/localization"
], function( BASE_MVC, _l ){
/* global Backbone, LoggableMixin */
//==============================================================================
/** @class Read only view for DatasetCollection.
 *  @name DCBaseView
 *
 *  @augments Backbone.View
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var DCBaseView = Backbone.View.extend( BASE_MVC.LoggableMixin ).extend({

    /** logger used to record this.log messages, commonly set to console */
    // comment this out to suppress log output
    //logger              : console,

    /**  */
    className   : "dataset-collection",
    /**  */
    fxSpeed     : 'fast',

    /**  */
    initialize  : function( attributes ){
        if( attributes.logger ){ this.logger = this.model.logger = attributes.logger; }
        this.log( 'DCBaseView.initialize:', attributes );
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
        $newRender.find( '.primary-actions' ).append( this._render_primaryActions() );
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
        // empty the old render, swap in the new render contents
        $( view ).queue( function( next ){
//TODO:?? change to replaceWith pattern?
            this.$el.empty().attr( 'class', view.className ).append( $newRender.children() );
            next();
        });
        // fade the new in
        if( fade ){
            $( view ).queue( function( next ){ this.$el.fadeIn( view.fxSpeed, next ); });
        }
        // trigger an event to know we're ready
        $( view ).queue( function( next ){
            this.trigger( 'rendered', view );
            next();
        });
    },

    /** set up js behaviors, event handlers for elements within the given container
     *  @param {jQuery} $container jq object that contains the elements to process (defaults to this.$el)
     */
    _setUpBehaviors : function( $container ){
        $container = $container || this.$el;
        make_popup_menus( $container );
        $container.find( '[title]' ).tooltip({ placement : 'bottom' });
    },

    // ........................................................................ titlebar buttons
    /** Render icon-button group for the common, most easily accessed actions.
     *  @returns {jQuery} rendered DOM or null
     */
    _render_primaryActions : function(){
        // override
        return [];
    },

    // ......................................................................... misc
    events : {
        'click .title-bar' : function( event ){
            this.trigger( 'expanded', this );
        }
    },

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'DCBaseView(' + modelString + ')';
    }
});

/** templates for DCBaseViews (skeleton and body) */
DCBaseView.templates = DCBaseView.prototype.templates = (function(){
// use closure to run underscore template fn only once at module load
    var skeletonTemplate = _.template([
        '<div class="dataset-collection">',
            '<div class="primary-actions"></div>',
            '<div class="title-bar clear" tabindex="0">',
                '<div class="title">',
                    '<span class="name"><%- collection.element_identifier %></span>',
                '</div>',
            '</div>',
            '<div class="details"></div>',
        '</div>'
    ].join( '' ));

    var bodyTemplate = _.template([
        '<div class="details">',
            '<div class="summary">', _l( 'A dataset collection.' ), '</div>',
        '</div>'
    ].join( '' ));

    // we override here in order to pass the localizer (_L) into the template scope - since we use it as a fn within
    return {
        skeleton : function( collectionJSON ){
            return skeletonTemplate({ _l: _l, collection: collectionJSON });
        },
        body : function( collectionJSON ){
            return bodyTemplate({ _l: _l, collection: collectionJSON });
        }
    };
}());


//==============================================================================
/** @class Read only view for DatasetCollectionElement.
 *  @name DCBaseView
 *
 *  @augments Backbone.View
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var DCEBaseView = BASE_MVC.ExpandableView.extend({

    /** logger used to record this.log messages, commonly set to console */
    // comment this out to suppress log output
    //logger              : console,

    /**  */
    className   : "dataset-collection-element collection-dataset dataset",
    /**  */
    fxSpeed     : 'fast',

    /**  */
    initialize  : function( attributes ){
        if( attributes.logger ){ this.logger = this.model.logger = attributes.logger; }
        this.log( 'DCEBaseView.initialize:', attributes );
        BASE_MVC.ExpandableView.prototype.initialize.call( this, attributes );
    },

    // ......................................................................... renderers
    /** Render the enclosing div of the hda body and, if expanded, the html in the body
     *  @returns {jQuery} rendered DOM
     */
    _renderDetails : function(){
        var $details = $( this.templates.details( this.model.toJSON() ) );
        this._setUpBehaviors( $details );
        // only render the body html if it's being shown
        if( this.expanded ){
            $details.show();
        }
        return $details;
    },

    // ......................................................................... events
    events : {
        // expand the body when the title is clicked or when in focus and space or enter is pressed
        'click .title-bar'      : '_clickTitleBar',
        'keydown .title-bar'    : '_keyDownTitleBar'
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
    },

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'DCEBaseView(' + modelString + ')';
    }
});

/** templates for DCBaseViews (skeleton and body) */
DCEBaseView.templates = DCEBaseView.prototype.templates = (function(){
// use closure to run underscore template fn only once at module load
    var skeletonTemplate = _.template([
        '<div class="dataset-collection-element collection-dataset dataset">',
            '<div class="primary-actions"></div>',
            '<div class="title-bar clear" tabindex="0">',
                '<span class="state-icon"></span>',
                '<div class="title">',
                    '<span class="name"><%- collection.element_identifier %></span>',
                '</div>',
            '</div>',
            '<div class="details"></div>',
        '</div>'
    ].join( '' ));

    var bodyTemplate = _.template([
        '<div class="details">',
            '<div class="summary">',
                _l( 'A dataset collection element.' ),
            '</div>',
        '</div>'
    ].join( '' ));

    // we override here in order to pass the localizer (_L) into the template scope - since we use it as a fn within
    return {
        skeleton : function( collectionJSON ){
            return skeletonTemplate({ _l: _l, collection: collectionJSON });
        },
        body : function( collectionJSON ){
            return bodyTemplate({ _l: _l, collection: collectionJSON });
        }
    };
}());


//==============================================================================
/** @class Read only view for DatasetCollectionElement.
 *  @name DCBaseView
 *
 *  @augments Backbone.View
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HDADCEBaseView = DCEBaseView.extend({

    /** logger used to record this.log messages, commonly set to console */
    // comment this out to suppress log output
    //logger              : console,

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'HDADCEBaseView(' + modelString + ')';
    }
});

/** templates for DCBaseViews (skeleton and body) */
HDADCEBaseView.templates = HDADCEBaseView.prototype.templates = (function(){
// use closure to run underscore template fn only once at module load
    var skeletonTemplate = _.template([
        '<div class="dataset-collection-element dataset">',
            '<div class="primary-actions"></div>',
            '<div class="title-bar clear" tabindex="0">',
                '<span class="state-icon"></span>',
                '<div class="title">',
//TODO:?? re-check this: in pairs the name and identifier are different - but not otherwise
                    '<span class="name"><%- element.element_identifier %></span>',
                '</div>',
//                '<% if( element.element_identifier !== hda.name ){ %>',
//                    '<div class="subtitle"><%- element.element_identifier %></div>',
//                '<% } %>',
            '</div>',
            '<div class="details"></div>',
        '</div>'
    ].join( '' ));

    var detailsTemplate = _.template([
        '<div class="details">',
            '<div class="summary">',
                '<% if( hda.misc_blurb ){ %>',
                    '<div class="blurb">',
                        '<span class="value"><%- hda.misc_blurb %></span>',
                    '</div>',
                '<% } %>',

                '<% if( hda.data_type ){ %>',
                    '<div class="datatype">',
                        '<label class="prompt">', _l( 'format' ), '</label>',
                        '<span class="value"><%- hda.data_type %></span>',
                    '</div>',
                '<% } %>',

                '<% if( hda.metadata_dbkey ){ %>',
                    '<div class="dbkey">',
                        '<label class="prompt">', _l( 'database' ), '</label>',
                        '<span class="value">',
                            '<%- hda.metadata_dbkey %>',
                        '</span>',
                    '</div>',
                '<% } %>',

                '<% if( hda.misc_info ){ %>',
                    '<div class="info">',
                        '<span class="value"><%- hda.misc_info %></span>',
                    '</div>',
                '<% } %>',
            '</div>',
            // end dataset-summary

            '<div class="actions clear">',
                '<div class="left"></div>',
                '<div class="right"></div>',
            '</div>',

            '<% if( !hda.deleted ){ %>',
                '<div class="tags-display"></div>',
                '<div class="annotation-display"></div>',

                '<div class="display-applications">',
                    //TODO: the following two should be compacted
                    '<% _.each( hda.display_apps, function( app ){ %>',
                        '<div class="display-application">',
                            '<span class="display-application-location"><%- app.label %></span> ',
                            '<span class="display-application-links">',
                                '<% _.each( app.links, function( link ){ %>',
                                    '<a target="<%= link.target %>" href="<%= link.href %>">',
                                        '<% print( _l( link.text ) ); %>',
                                    '</a> ',
                                '<% }); %>',
                            '</span>',
                        '</div>',
                    '<% }); %>',

                    '<% _.each( hda.display_types, function( app ){ %>',
                        '<div class="display-application">',
                            '<span class="display-application-location"><%- app.label %></span> ',
                            '<span class="display-application-links">',
                                '<% _.each( app.links, function( link ){ %>',
                                    '<a target="<%= link.target %>" href="<%= link.href %>">',
                                        '<% print( _l( link.text ) ); %>',
                                    '</a> ',
                                '<% }); %>',
                            '</span>',
                        '</div>',
                    '<% }); %>',
                '</div>',

                '<% if( hda.peek ){ %>',
                    '<pre class="dataset-peek"><%= hda.peek %></pre>',
                '<% } %>',

            '<% } %>',
            // end if !deleted

        '</div>'
    ].join( '' ));

    // we override here in order to pass the localizer (_L) into the template scope - since we use it as a fn within
    return {
        skeleton : function( json ){
            return skeletonTemplate({ _l: _l, element: json, hda: json.object });
        },
        details : function( json ){
            return detailsTemplate({ _l: _l, element: json, hda: json.object });
        }
    };
}());


//==============================================================================
/** @class Read only view for DatasetCollectionElement.
 *  @name DCBaseView
 *
 *  @augments Backbone.View
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var DCDCEBaseView = DCEBaseView.extend({

    /** logger used to record this.log messages, commonly set to console */
    // comment this out to suppress log output
    //logger              : console,

    // ......................................................................... misc
    /** String representation */
    expand : function(){
        this.trigger( 'expanded', this );
    },

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'DCDCEBaseView(' + modelString + ')';
    }
});

/** templates for DCBaseViews (skeleton and body) */
DCDCEBaseView.templates = DCDCEBaseView.prototype.templates = (function(){
// use closure to run underscore template fn only once at module load
    var skeletonTemplate = _.template([
        '<div class="dataset-collection-element dataset-collection">',
            '<div class="primary-actions"></div>',
            '<div class="title-bar clear" tabindex="0">',
                '<span class="state-icon"></span>',
                '<div class="title">',
                    '<span class="name"><%- element.element_identifier %></span>',
                '</div>',
//TODO: currently correct, but needs logic if more nested types are added
                '<div class="subtitle">', _l( 'paired datasets' ), '</div>',
            '</div>',
            '<div class="details"></div>',
        '</div>'
    ].join( '' ));

    // we override here in order to pass the localizer (_L) into the template scope - since we use it as a fn within
    return {
        skeleton : function( json ){
            return skeletonTemplate({ _l: _l, element: json, collection: json.object });
        }
    };
}());


//==============================================================================
    return {
        DCBaseView          : DCBaseView,
        DCEBaseView         : DCEBaseView,
        HDADCEBaseView      : HDADCEBaseView,
        DCDCEBaseView       : DCDCEBaseView
    };
});
