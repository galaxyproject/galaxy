<template>
    <div>
        <DscUI
            v-if="dataset_collection"
            v-bind="$attrs"
            v-on="$listeners"
            :dsc="dataset_collection"
            :showTags="true"
            v-on:update:expanded="expandCollection"
        />
        <DatasetCollectionContentProvider
            v-for="collection in expandedCollections"
            :key="collection.id"
            :id="collection.contents_url"
            v-slot="{ item, loading }"
        >
            <DatasetCollectionContents :collectionContents="item" v-if="item" />
        </DatasetCollectionContentProvider>
    </div>
</template>
<script>
import DscUI from "./DscUI";
import { DatasetCollection } from "../../model/DatasetCollection";
import { DatasetCollectionContentProvider } from "components/History/providers/DatasetProvider";
import DatasetCollectionContents from "components/History/ContentItem/DatasetCollection/DatasetCollectionContents";

export default {
    components: {
        DatasetCollectionContentProvider,
        DatasetCollectionContents,
        DscUI,
    },
    props: {
        item: { type: Object, required: true },
        element_count: { type: Number, required: false },
    },
    data() {
        return { expandedCollections: [] };
    },
    computed: {
        dataset_collection() {
            var rawObject = this.item;
            if (rawObject.model_class === "DatasetCollectionElement") {
                rawObject = this.item.object;
                rawObject.name = this.item.element_identifier;
                rawObject.contents_url = this.item.contents_url || rawObject.contents_url;
                rawObject.element_count = this.element_count;
                // TODO: dataset collections should probably be able to determine their own state?
                rawObject.populated_state = "ok";
            }
            return new DatasetCollection(rawObject);
        },
    },
    methods: {
        expandCollection(coll) {
            const index = this.expandedCollections.indexOf(coll);
            if (index > -1) {
                this.expandedCollections.splice(index, 1);
            } else {
                this.expandedCollections.push(coll);
            }
        },
    },
};
</script>
