define([
    "mvc/base-mvc",
    "utils/localization"
], function( baseMVC, _l ){
/* global Backbone */
//==============================================================================
/** @class Read only view for history content views to extend.
 *  @name HistoryContentBaseView
 *
 *  @augments Backbone.View
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HistoryContentBaseView = Backbone.View.extend( baseMVC.LoggableMixin ).extend(
/** @lends HistoryContentBaseView.prototype */{
});

//TODO: not sure base view class is warranted or even wise


//==============================================================================
    return {
        HistoryContentBaseView : HistoryContentBaseView
    };
});
