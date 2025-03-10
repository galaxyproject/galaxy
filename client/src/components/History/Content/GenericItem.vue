<template>
    <component :is="providerComponent" :id="itemId" v-slot="{ result: item, loading }" auto-refresh>
        <LoadingSpan v-if="loading" message="Loading dataset" />
        <div v-else>
            <ContentItem
                :id="item.hid ?? item.element_index + 1"
                add-highlight-btn
                is-history-item
                :item="item?.object || item"
                :name="item.name || item.element_identifier"
                :expand-dataset="expandDataset"
                :is-dataset="item.history_content_type == 'dataset' || item.element_type == 'hda'"
                @update:expand-dataset="expandDataset = $event"
                @view-collection="viewCollection = !viewCollection"
                @delete="onDelete"
                @toggleHighlights="onHighlight(item)"
                @undelete="onUndelete(item)"
                @unhide="onUnhide(item)" />
            <div v-if="viewCollection">
                <GenericElement :dsc="item?.object || item" />
            </div>
        </div>
    </component>
</template>

<script>
import LoadingSpan from "components/LoadingSpan";
import { Toast } from "composables/toast";
import { mapActions } from "pinia";

import { deleteContent, updateContentFields } from "@/components/History/model/queries";
import { DatasetCollectionProvider, DatasetProvider } from "@/components/providers";
import { DatasetCollectionElementProvider } from "@/components/providers/storeProviders";
import { useHistoryStore } from "@/stores/historyStore";
import { errorMessageAsString } from "@/utils/simple-error";

import ContentItem from "./ContentItem";
import GenericElement from "./GenericElement";

export default {
    components: {
        DatasetCollectionElementProvider,
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
            switch (this.itemSrc) {
                case "hda":
                    return "DatasetProvider";
                case "hdca":
                    return "DatasetCollectionProvider";
                case "dce":
                    return "DatasetCollectionElementProvider";
                default:
                    // Failed on LDDAs https://github.com/galaxyproject/galaxy/issues/19687
                    throw Error(`Unknown element src ${this.itemSrc}`);
            }
        },
    },
    methods: {
        ...mapActions(useHistoryStore, ["applyFilters"]),
        async onDelete(item, recursive = false) {
            try {
                await deleteContent(item, { recursive: recursive });
            } catch (error) {
                this.onError(error, "Failed to delete item");
            }
        },
        onError(e, title = "Error") {
            const error = errorMessageAsString(e, "Dataset operation failed.");
            Toast.error(error, title);
        },
        async onUndelete(item) {
            try {
                await updateContentFields(item, { deleted: false });
            } catch (error) {
                this.onError(error, "Failed to undelete item");
            }
        },
        async onHide(item) {
            try {
                await updateContentFields(item, { visible: false });
            } catch (error) {
                this.onError(error, "Failed to hide item");
            }
        },
        async onUnhide(item) {
            try {
                await updateContentFields(item, { visible: true });
            } catch (error) {
                this.onError(error, "Failed to unhide item");
            }
        },
        async onHighlight(item) {
            const { history_id } = item;
            const filters = {
                deleted: item.deleted,
                visible: item.visible,
                related: item.hid,
            };
            try {
                await this.applyFilters(history_id, filters);
            } catch (error) {
                this.onError(error, "Failed to highlight related items");
            }
        },
    },
};
</script>
