<template>
    <component :is="providerComponent" :id="itemId" v-slot="{ result: item, loading }" auto-refresh>
        <loading-span v-if="loading" message="Loading dataset" />
        <div v-else>
            <ContentItem
                :id="item.hid"
                add-highlight-btn
                is-history-item
                :item="item"
                :name="item.name"
                :expand-dataset="expandDataset"
                :is-dataset="item.history_content_type == 'dataset'"
                @update:expand-dataset="expandDataset = $event"
                @view-collection="viewCollection = !viewCollection"
                @delete="onDelete(item)"
                @toggleHighlights="onHighlight(item)"
                @undelete="onUndelete(item)"
                @unhide="onUnhide(item)" />
            <div v-if="viewCollection">
                <GenericElement :dsc="item" />
            </div>
        </div>
    </component>
</template>

<script>
import LoadingSpan from "components/LoadingSpan";
import { DatasetCollectionProvider, DatasetProvider } from "components/providers";
import { deleteContent, updateContentFields } from "components/History/model/queries";
import { HistoryFilters } from "components/History/HistoryFilters";
import ContentItem from "./ContentItem";
import GenericElement from "./GenericElement";
import { mapActions } from "pinia";
import { useHistoryStore } from "@/stores/historyStore";

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
        ...mapActions(useHistoryStore, ["applyFilterText"]),
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
        async onHighlight(item) {
            const { history_id } = item;
            const filterSettings = {
                "deleted:": item.deleted,
                "visible:": item.visible,
                "related:": item.hid,
            };
            const filterText = HistoryFilters.getFilterText(filterSettings);
            try {
                await this.applyFilterText(history_id, filterText);
            } catch (error) {
                this.onError(error);
            }
        },
    },
};
</script>
