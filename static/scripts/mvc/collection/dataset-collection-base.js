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

//TODO: render has been removed from the inheritance chain here, so this won't work when called as is

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'DCBaseView(' + modelString + ')';
    }
});

/** templates for DCBaseViews (skeleton and body) */
DCBaseView.templates = (function(){
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
            '<div class="dataset-primary-actions"></div>',
            '<div class="dataset-title-bar clear" tabindex="0">',
                '<span class="dataset-state-icon state-icon"></span>',
                '<div class="dataset-title">',
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


//TODO: unused
////==============================================================================
///** @class Read only view for DatasetCollectionElement.
// *  @name DCEBaseView
// *
// *  @augments Backbone.View
// *  @borrows LoggableMixin#logger as #logger
// *  @borrows LoggableMixin#log as #log
// *  @constructs
// */
//var NestedDCBaseView = DCBaseView.extend({
//
//    logger : console,
//
//    /**  */
//    initialize  : function( attributes ){
//        if( attributes.logger ){ this.logger = this.model.logger = attributes.logger; }
//        this.warn( this + '.initialize:', attributes );
//        DCBaseView.prototype.initialize.call( this, attributes );
//    },
//
//    _template : function(){
//        this.debug( this.model );
//        this.debug( this.model.toJSON() );
//        return NestedDCBaseView.templates.skeleton( this.model.toJSON() );
//    },
//
//    // ......................................................................... misc
//    /** String representation */
//    toString : function(){
//        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
//        return 'NestedDCBaseView(' + modelString + ')';
//    }
//});
//
////------------------------------------------------------------------------------ TEMPLATES
////TODO: possibly break these out into a sep. module
//NestedDCBaseView.templates = (function(){
//    var skeleton = _.template([
//        '<div class="dataset hda history-panel-hda state-ok">',
//            '<div class="dataset-primary-actions"></div>',
//            '<div class="dataset-title-bar clear" tabindex="0">',
//                '<div class="dataset-title">',
//                    '<span class="dataset-name"><%= collection.name %></span>',
//                '</div>',
//            '</div>',
//        '</div>'
//    ].join( '' ));
//    // we override here in order to pass the localizer (_L) into the template scope - since we use it as a fn within
//    return {
//        skeleton : function( json ){
//            return skeleton({ _l: _l, collection: json });
//        }
//    };
//}());


//==============================================================================
    return {
        DCBaseView          : DCBaseView,
        //NestedDCBaseView    : NestedDCBaseView,
    };
});
