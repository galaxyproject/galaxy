<template>
    <div>
        <DscUI
            v-if="datasetCollection"
            v-bind="$attrs"
            v-on="$listeners"
            :dsc="datasetCollection"
            :show-tags="true"
            @viewCollection="toggleExpand"
            @hide="onHide(datasetCollection)"
            @unhide="onUnhide(datasetCollection)"
            @delete="onDelete(datasetCollection, $event)"
            @undelete="onUndelete(datasetCollection)" />
        <DatasetCollectionContentProvider v-if="expand" :id="datasetCollection.contents_url" v-slot="{ item, loading }">
            <b-spinner v-if="loading">Loading Dataset Collection...</b-spinner>
            <DatasetCollectionContents v-else :collection-contents="item" />
        </DatasetCollectionContentProvider>
    </div>
</template>
<script>
import { deleteDatasetCollection, updateContentFields } from "../../model/queries";
import { cacheContent } from "components/providers/History/caching";
import { DatasetCollection } from "../../model/DatasetCollection";
import DscUI from "components/History/ContentItem/DatasetCollection/DscUI";
import { DatasetCollectionContentProvider } from "components/providers";
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
        return { expand: false };
    },
    computed: {
        datasetCollection() {
            var rawObject = this.item;
            if (rawObject.model_class === "DatasetCollectionElement") {
                rawObject = this.item.object;
                rawObject.name = this.item.element_identifier;
                rawObject.contents_url = this.item.contents_url || rawObject.contents_url;
                rawObject.element_count = this.element_count;
                rawObject.populated_state = "ok";
            }
            return new DatasetCollection(rawObject);
        },
    },
    methods: {
        toggleExpand() {
            this.expand = !this.expand;
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
