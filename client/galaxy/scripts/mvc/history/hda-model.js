define([
    "mvc/dataset/dataset-model",
    "mvc/history/history-content-model",
    "mvc/base-mvc",
    "utils/localization"
], function( DATASET, HISTORY_CONTENT, BASE_MVC, _l ){
'use strict';

//==============================================================================
var _super = DATASET.DatasetAssociation,
    hcontentMixin = HISTORY_CONTENT.HistoryContentMixin;
/** @class (HDA) model for a Galaxy dataset contained in and related to a history.
 */
var HistoryDatasetAssociation = _super.extend( BASE_MVC.mixin( hcontentMixin,
/** @lends HistoryDatasetAssociation.prototype */{

    /** default attributes for a model */
    defaults : _.extend( {}, _super.prototype.defaults, hcontentMixin.defaults, {
        history_content_type: 'dataset',
        model_class         : 'HistoryDatasetAssociation'
    }),
}));

//==============================================================================
    return {
        HistoryDatasetAssociation   : HistoryDatasetAssociation
    };
});
