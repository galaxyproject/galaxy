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
    //PRECONDITION: expects to be mixed into an BASE_MVC.ExpandableView
    initialize : function( attributes ){
        
    }

//TODO: render title with HID
//TODO: render based on visiblility (HDA only)

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
var HistoryContentBaseView = BASE_MVC.ExpandableView.extend(
/** @lends HistoryContentBaseView.prototype */HistoryContentViewMixin );

//TODO: not sure base view class is warranted or even wise


//==============================================================================
    return {
        HistoryContentViewMixin : HistoryContentViewMixin,
        HistoryContentBaseView  : HistoryContentBaseView
    };
});
