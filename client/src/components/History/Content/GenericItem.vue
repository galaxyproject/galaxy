<script setup lang="ts">
import { useIntersectionObserver } from "@vueuse/core";
import { computed, ref } from "vue";

import type { HistoryItemSummary } from "@/api";
import { deleteContent, updateContentFields } from "@/components/History/model/queries";
import { DatasetCollectionProvider, DatasetProvider } from "@/components/providers";
import { DatasetCollectionElementProvider } from "@/components/providers/storeProviders";
import { Toast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { errorMessageAsString } from "@/utils/simple-error";

import ContentItem from "./ContentItem.vue";
import GenericElement from "./GenericElement.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const props = defineProps<{
    itemId: string;
    itemSrc: string;
}>();

const historyStore = useHistoryStore();

const viewCollection = ref(false);
const expandDataset = ref(false);
const view = ref(props.itemSrc === "hdca" ? "collection" : "element");

const providerComponent = computed(() => {
    switch (props.itemSrc) {
        case "hda":
            return DatasetProvider;
        case "hdca":
            return DatasetCollectionProvider;
        case "dce":
            return DatasetCollectionElementProvider;
        default:
            // Failed on LDDAs https://github.com/galaxyproject/galaxy/issues/19687
            throw new Error(`Unknown element src ${props.itemSrc}`);
    }
});

const containerEl = ref<HTMLElement | null>(null);
const hasBeenVisible = ref(false);
const { stop: stopObserver } = useIntersectionObserver(containerEl, ([entry]) => {
    if (entry?.isIntersecting) {
        hasBeenVisible.value = true;
        stopObserver();
    }
});

async function onDelete(item: HistoryItemSummary, recursive = false) {
    try {
        await deleteContent(item, { recursive });
    } catch (e) {
        onError(e, "Failed to delete item");
    }
}

function onError(e: unknown, title = "Error") {
    Toast.error(errorMessageAsString(e, "Dataset operation failed."), title);
}

async function onUndelete(item: HistoryItemSummary) {
    try {
        await updateContentFields(item, { deleted: false });
    } catch (e) {
        onError(e, "Failed to undelete item");
    }
}

async function onUnhide(item: HistoryItemSummary) {
    try {
        await updateContentFields(item, { visible: true });
    } catch (e) {
        onError(e, "Failed to unhide item");
    }
}

async function onHighlight(item: HistoryItemSummary) {
    try {
        await historyStore.applyFilters(item.history_id, {
            deleted: item.deleted,
            visible: item.visible,
            related: item.hid,
        });
    } catch (e) {
        onError(e, "Failed to highlight related items");
    }
}

function onViewCollection(collection: any) {
    if (view.value === "collection" && collection.model_class === "HistoryDatasetCollectionAssociation") {
        view.value = "element";
    }
    viewCollection.value = !viewCollection.value;
}
</script>

<template>
    <div ref="containerEl">
        <component
            :is="providerComponent"
            v-if="hasBeenVisible"
            :id="itemId"
            :key="view"
            v-slot="{ result: item, loading }"
            :view="view"
            auto-refresh>
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
                    @view-collection="onViewCollection"
                    @delete="onDelete"
                    @toggleHighlights="onHighlight(item)"
                    @undelete="onUndelete(item)"
                    @unhide="onUnhide(item)" />
                <div v-if="viewCollection">
                    <GenericElement :dsc="item?.object || item" />
                </div>
            </div>
        </component>
    </div>
</template>
