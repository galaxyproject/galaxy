<template>
    <div>
        <DscUI
            v-if="dataset_collection"
            v-bind="$attrs"
            v-on="$listeners"
            :dsc="dataset_collection"
            :showTags="true"
            v-on:update:expanded="expandCollection"
            @hideCollection="onHide(dataset_collection)"
            @unhideCollection="onUnhide(dataset_collection, $event)"
            @deleteCollection="onDelete(dataset_collection, $event)"
            @undeleteCollection="onUndelete(dataset_collection)"
        />
        <DatasetCollectionContentProvider
            v-for="collection in expandedCollections"
            :key="collection.id"
            :id="collection.contents_url"
            v-slot="{ item, loading }"
        >
            <b-spinner v-if="loading">Loading Dataset Collection...</b-spinner>
            <DatasetCollectionContents v-else :collectionContents="item" />
        </DatasetCollectionContentProvider>
    </div>
</template>
<script>
import { deleteDatasetCollection, updateContentFields } from "../History/model/queries";
import { cacheContent } from "../History/caching";
import { DatasetCollection } from "../History/model/DatasetCollection";
import DscUI from "../History/ContentItem/DatasetCollection/DscUI";
import { DatasetCollectionContentProvider } from "./providers";
import DatasetCollectionContents from "./DatasetCollectionContents";

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
        async onDelete(collection, flags = {}) {
            const { recursive = false, purge = false } = flags;
            const result = await deleteDatasetCollection(collection, recursive, purge);
            if (result.deleted) {
                const newFields = Object.assign(collection, {
                    isDeleted: result.deleted,
                });
                await cacheContent(newFields);
            }
        },

        async onUndelete(collection) {
            const result = await updateContentFields(collection, { deleted: false });
            if (result.deleted === false) {
                const newFields = Object.assign(collection, {
                    isDeleted: result.deleted,
                });
                await cacheContent(newFields);
            }
        },
        async onHide(collection) {
            const result = await updateContentFields(collection, { visible: false });
            if (result.visible === false) {
                const newFields = Object.assign(collection, {
                    isVisible: result.visible,
                });
                await cacheContent(newFields);
            }
        },
        async onUnhide(collection) {
            const result = await updateContentFields(collection, { visible: true });
            if (result.visible) {
                const newFields = Object.assign(collection, {
                    isVisible: result.visible,
                });
                await cacheContent(newFields);
            }
        },
    },
};
</script>
