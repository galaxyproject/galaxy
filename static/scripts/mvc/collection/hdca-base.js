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

    /**  */
    className   : "dataset hda history-panel-hda",

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
                    '<span class="hda-hid"><%- collection.hid %></span> ',
                    '<span class="dataset-name"><%- collection.name %></span>',
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
