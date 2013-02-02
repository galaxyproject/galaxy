define(["libs/backbone/backbone-relational"], function() {

/**
 * Dataset metedata.
 */
var DatasetMetadata = Backbone.RelationalModel.extend({});

/**
 * A dataset. In Galaxy, datasets are associated with a history, so
 * this object is also known as a HistoryDatasetAssociation.
 */
var Dataset = Backbone.RelationalModel.extend({
    defaults: {
        id: '',
        type: '',
        name: '',
        hda_ldda: 'hda',
        metadata: null
    },

    initialize: function() {
        // -- Create and initialize metadata. -- 

        var metadata = new DatasetMetadata();

        // Move metadata from dataset attributes to metadata object.
        _.each(_.keys(this.attributes), function(k) { 
            if (k.indexOf('metadata_') === 0) {
                // Found metadata.
                var new_key = k.split('metadata_')[1];
                metadata.set(new_key, this.attributes[k]);
                delete this.attributes[k];
            }
        }, this);

        this.set('metadata', metadata);
    },

    /**
     * Returns dataset metadata for a given attribute.
     */
    get_metadata: function(attribute) {
        return this.attributes.metadata.get(attribute);
    },

    urlRoot: galaxy_paths.get('datasets_url')
});

var DatasetCollection = Backbone.Collection.extend({
    model: Dataset
});

return {
	Dataset: Dataset,
	DatasetCollection: DatasetCollection
};

});
