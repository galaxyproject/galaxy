define([
    "mvc/base-mvc",
    "mvc/collection/dataset-collection-base",
    "mvc/history/history-content-base-view",
    "utils/localization"
], function( BASE_MVC, DC_BASE, HISTORY_CONTENT_BASE_VIEW, _l ){
/* global Backbone, LoggableMixin */
//==============================================================================
var HCVMixin = HISTORY_CONTENT_BASE_VIEW.HistoryContentViewMixin,
    _super = DC_BASE.DCBaseView;
/** @class Read only view for HistoryDatasetCollectionAssociation.
 *  @name
 *
 *  @augments Backbone.View
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HDCABaseView = _super.extend( BASE_MVC.mixin( HCVMixin, {

    /** logger used to record this.log messages, commonly set to console */
    // comment this out to suppress log output
    //logger              : console,

//TODO: not a dataset
    /**  */
    className   : "dataset hdca history-panel-hda",

    /**  */
    initialize  : function( attributes ){
        if( attributes.logger ){ this.logger = this.model.logger = attributes.logger; }
        this.log( this + '.initialize:', attributes );
        _super.prototype.initialize.call( this, attributes );
        HCVMixin.initialize.call( this, attributes );
    },

    /**  */
    _template : function(){
        return HDCABaseView.templates.skeleton( this.model.toJSON() );
    },

    /**  */
    events : _.extend( _.clone( HCVMixin.events ), {
    }),

    /**  */
    _renderBody : function(){
        // override this
        var $body = $( _super.templates.body( this.model.toJSON() ) );
        if( this.expanded ){
            $body.show();
        }
        return $body;
    },

    /** In this override, do not slide down or render any body/details - allow the container to handle it
     *  @fires expanded when a body has been expanded
     */
    expand : function(){
        this.warn( this + '.expand' );
        var contentView = this;

        // fetch first if no details in the model
        if( this.model.inReadyState() && !this.model.hasDetails() ){
            // we need the change event on HDCA's for the elements to be processed - so silent == false
            this.model.fetch().always( function( model ){
                contentView.expanded = true;
                contentView.trigger( 'expanded', contentView );
            });
        } else {
            contentView.expanded = true;
            contentView.trigger( 'expanded', contentView );
        }
    },

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'HDCABaseView(' + modelString + ')';
    }
}));

/** templates for HDCAs (skeleton and body) */
HDCABaseView.templates = HDCABaseView.prototype.templates = (function(){
// use closure to run underscore template fn only once at module load
    var skeletonTemplate = _.template([
//TODO: not a dataset
        '<div class="dataset hdca">',
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
            '<div class="selector"><span class="fa fa-2x fa-square-o"></span></div>',
            '<div class="primary-actions"></div>',
            '<div class="title-bar clear" tabindex="0">',
                '<span class="state-icon"></span>',
                '<div class="title">',
                    '<span class="hid"><%- collection.hid %></span> ',
                    '<span class="name"><%- collection.name %></span>',
                '</div>',
                '<div class="subtitle">',
//TODO: remove from template logic
                    '<% if( collection.collection_type === "list" ){ %>',
                        _l( 'a list of datasets' ),
                    '<% } else if( collection.collection_type === "paired" ){ %>',
                        _l( 'a pair of datasets' ),
                    '<% } else if( collection.collection_type === "list:paired" ){ %>',
                        _l( 'a list of paired datasets' ),
                    '<% } %>',
                '</div>',
            '</div>',
            '<div class="details"></div>',
        '</div>'
    ].join( '' ));

    var bodyTemplate = _.template([
        '<div class="details">',
            '<div class="summary">',
            _l( 'A dataset collection.' ),
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
    return {
        HDCABaseView        : HDCABaseView
    };
});
