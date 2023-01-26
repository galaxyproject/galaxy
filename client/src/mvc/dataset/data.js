import _ from "underscore";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";

//temporary
import { replaceChildrenWithComponent } from "utils/mountVueComponent";
import TabularChunkedView from "components/Visualizations/Tabular/TabularChunkedView.vue";

/**
 * Dataset metedata.
 */
var DatasetMetadata = Backbone.Model.extend({});

/**
 * A dataset. In Galaxy, datasets are associated with a history, so
 * this object is also known as a HistoryDatasetAssociation.
 */
export var Dataset = Backbone.Model.extend({
    defaults: {
        id: "",
        type: "",
        name: "",
        hda_ldda: "hda",
        metadata: null,
    },

    initialize: function () {
        // Metadata can be passed in as a model or a set of attributes; if it's
        // already a model, there's no need to set metadata.
        if (!this.get("metadata")) {
            this._set_metadata();
        }

        // Update metadata on change.
        this.on("change", this._set_metadata, this);
    },

    _set_metadata: function () {
        var metadata = new DatasetMetadata();

        // Move metadata from dataset attributes to metadata object.
        _.each(
            _.keys(this.attributes),
            function (k) {
                if (k.indexOf("metadata_") === 0) {
                    // Found metadata.
                    var new_key = k.split("metadata_")[1];
                    metadata.set(new_key, this.attributes[k]);
                    delete this.attributes[k];
                }
            },
            this
        );

        // Because this is an internal change, silence it.
        this.set("metadata", metadata, { silent: true });
    },

    /**
     * Returns dataset metadata for a given attribute.
     */
    get_metadata: function (attribute) {
        return this.attributes.metadata.get(attribute);
    },

    urlRoot: `${getAppRoot()}api/datasets`,
});

export var DatasetCollection = Backbone.Collection.extend({
    model: Dataset,
});

export const createTabularDatasetChunkedView = (options) => {
    // We'll always have a parent_elt in options, so create a div and insert it into that.
    return replaceChildrenWithComponent(options.parent_elt, TabularChunkedView, { options });
};
