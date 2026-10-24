<script setup lang="ts">
import { useIntersectionObserver } from "@vueuse/core";
import { computed, nextTick, ref, watch } from "vue";

import type { HistoryItemSummary } from "@/api";
import { deleteContent, updateContentFields } from "@/components/History/model/queries";
import { DatasetCollectionProvider, DatasetProvider } from "@/components/providers";
import { DatasetCollectionElementProvider } from "@/components/providers/storeProviders";
import { Toast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { errorMessageAsString } from "@/utils/simple-error";

import ContentItem from "./ContentItem.vue";
import GenericElement from "./GenericElement.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const props = withDefaults(
    defineProps<{
        itemId: string;
        itemSrc: string;
        expanded?: boolean;
        scrollOnExpand?: boolean;
    }>(),
    { expanded: undefined },
);

const emit = defineEmits<{ (e: "update:expanded", value: boolean): void }>();

const historyStore = useHistoryStore();

const viewCollection = ref(false);
const expandDataset = ref(false);
// An item the user just toggled is already in view; only scroll to targets expanded from elsewhere.
let userToggled = false;
function setExpanded(value: boolean) {
    userToggled = true;
    expandDataset.value = value;
    emit("update:expanded", value);
}
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

watch(
    () => props.expanded,
    async (value) => {
        const scroll = props.scrollOnExpand && !userToggled;
        userToggled = false;
        if (value === undefined) {
            return;
        }
        expandDataset.value = props.itemSrc === "hda" && value;
        viewCollection.value = props.itemSrc !== "hda" && value;
        if (value) {
            // URL targets must load even when they start below the viewport.
            hasBeenVisible.value = true;
            if (props.itemSrc === "hdca") {
                view.value = "element";
            }
            await nextTick();
            if (scroll) {
                // The target is still loading and will grow, so align its top. Jump rather than
                // smooth scroll: lazy items passed mid-scroll load, grow and push the target off screen.
                containerEl.value?.scrollIntoView({ block: "start" });
            }
        }
    },
    { immediate: true },
);

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
    userToggled = true;
    viewCollection.value = !viewCollection.value;
    emit("update:expanded", viewCollection.value);
}
</script>

<template>
    <div ref="containerEl">
        <component
            :is="providerComponent"
            v-if="hasBeenVisible"
            :id="itemId"
            :key="view"
            v-slot="{ result: item, loading, error }"
            :view="view"
            auto-refresh>
            <GAlert v-if="error" variant="danger" show>{{ errorMessageAsString(error) }}</GAlert>
            <LoadingSpan v-else-if="loading" message="Loading dataset" />
            <div v-else>
                <ContentItem
                    :id="item.hid ?? item.element_index + 1"
                    add-highlight-btn
                    is-history-item
                    :item="item?.object || item"
                    :name="item.name || item.element_identifier"
                    :expand-dataset="expandDataset"
                    :is-dataset="item.history_content_type == 'dataset' || item.element_type == 'hda'"
                    @update:expand-dataset="setExpanded"
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
