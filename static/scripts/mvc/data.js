/**
 * A dataset. In Galaxy, datasets are associated with a history, so
 * this object is also known as a HistoryDatasetAssociation.
 */
var Dataset = Backbone.RelationalModel.extend({
    defaults: {
        id: "",
        type: "",
        name: "",
        hda_ldda: ""
    } 
});

var DatasetCollection = Backbone.Collection.extend({
    model: Dataset
});