<template>
    <component :is="providerComponent" :id="itemId" auto-refresh v-slot="{ result: item, loading }">
        <loading-span v-if="loading" message="Loading dataset" />
        <div v-else>
            <ContentItem
                :item="item"
                :id="item.hid"
                :name="item.name"
                :expand-dataset="expandDataset"
                :is-dataset="item.history_content_type == 'dataset'"
                @update:expand-dataset="expandDataset = $event"
                @view-collection="viewCollection = !viewCollection"
                @delete="onDelete"
                @undelete="onUndelete"
                @unhide="onUnhide" />
            <div v-if="viewCollection">
                <div v-for="(collectionItem, collectionIndex) in item.elements" :key="collectionIndex">
                    <GenericElement :item="collectionItem" />
                </div>
            </div>
        </div>
    </component>
</template>

<script>
import LoadingSpan from "components/LoadingSpan";
import { DatasetCollectionProvider, DatasetProvider } from "components/providers";
import { deleteContent, updateContentFields } from "components/History/model/queries";
import ContentItem from "./ContentItem";
import GenericElement from "./GenericElement";

export default {
    components: {
        ContentItem,
        GenericElement,
        DatasetProvider,
        DatasetCollectionProvider,
        LoadingSpan,
    },
    props: {
        itemId: {
            type: String,
            required: true,
        },
        itemSrc: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            viewCollection: false,
            expandDataset: false,
        };
    },
    computed: {
        providerComponent() {
            return this.itemSrc == "hda" ? "DatasetProvider" : "DatasetCollectionProvider";
        },
    },
    methods: {
        onDelete(item) {
            deleteContent(item);
        },
        onUndelete(item) {
            updateContentFields(item, { deleted: false });
        },
        onHide(item) {
            updateContentFields(item, { visible: false });
        },
        onUnhide(item) {
            updateContentFields(item, { visible: true });
        },
    },
};
</script>
