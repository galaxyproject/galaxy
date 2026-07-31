<!-- When a dataset collection is being viewed, this panel shows the contents of that collection -->

<script setup lang="ts">
import { computed, ref, watch } from "vue";

import {
    canMutateHistory,
    type CollectionEntry,
    type DCESummary,
    type HDCASummary,
    type HistoryItemSummary,
    type HistorySummary,
    isCollectionElement,
    isHDCA,
    type SubCollection,
} from "@/api";
import ExpandedItems from "@/components/History/Content/ExpandedItems";
import { HistoryFilters } from "@/components/History/HistoryFilters";
import { updateContentFields } from "@/components/History/model/queries";
import { useSelectedItems } from "@/composables/selectedItems/selectedItems";
import { useCollectionElementsStore } from "@/stores/collectionElementsStore";
import { setItemDragstart } from "@/utils/setDrag";
import { errorMessageAsString } from "@/utils/simple-error";

import CollectionDetails from "./CollectionDetails.vue";
import CollectionNavigation from "./CollectionNavigation.vue";
import CollectionOperations from "./CollectionOperations.vue";
import Alert from "@/components/Alert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import CollectionCreatorIndex from "@/components/Collections/CollectionCreatorIndex.vue";
import ContentItem from "@/components/History/Content/ContentItem.vue";
import ListingLayout from "@/components/History/Layout/ListingLayout.vue";

interface Props {
    history: HistorySummary;
    selectedCollections: CollectionEntry[];
    showControls?: boolean;
    filterable?: boolean;
    multiView?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    showControls: true,
    filterable: false,
});

function onCreatedCollection() {
    resetSelection();
    setShowSelection(false);
    showCollectionCreator.value = false;
}

const collectionElementsStore = useCollectionElementsStore();

const emit = defineEmits<{
    (e: "view-collection", collection: CollectionEntry): void;
    (e: "update:selected-collections", collections: CollectionEntry[]): void;
}>();

const offset = ref(0);

const dsc = computed(() => {
    const currentCollection = props.selectedCollections[props.selectedCollections.length - 1];
    if (currentCollection === undefined) {
        throw new Error("No collection selected");
    }
    return currentCollection as HDCASummary;
});
watch(
    () => [dsc.value, offset.value],
    () => {
        collectionElementsStore.fetchMissingElements(dsc.value, offset.value);
    },
    { immediate: true },
);

const collectionElements = computed(() => collectionElementsStore.getCollectionElements(dsc.value) ?? []);
const loading = computed(() => collectionElementsStore.isLoadingCollectionElements(dsc.value));
const error = computed(() => collectionElementsStore.getLoadingCollectionElementsError(dsc.value));
const jobState = computed(() => ("job_state_summary" in dsc.value ? dsc.value.job_state_summary : undefined));
const populatedStateMsg = computed(() =>
    "populated_state_message" in dsc.value ? dsc.value.populated_state_message : undefined,
);
const rootCollection = computed(() => {
    if (isHDCA(props.selectedCollections[0])) {
        return props.selectedCollections[0];
    } else {
        throw new Error("Root collection must be an HistoryDatasetCollectionAssociation");
    }
});
const isRoot = computed(() => dsc.value == rootCollection.value);
const canEdit = computed(() => isRoot.value && canMutateHistory(props.history));

/** Selection inside a collection uses the same composable as the history
 * panel, so selecting behaves identically in both places: a select toggle,
 * click to select without opening the item, and shift for a range. */
const showCollectionCreator = ref(false);

/** Stable key for an element, used for selection and refs. */
function elementKey(item: DCESummary) {
    return String(item.element_identifier ?? item.element_index);
}

const {
    selectedItems,
    showSelection,
    selectionSize,
    setShowSelection,
    isRangeSelectAnchor,
    isSelected,
    setSelected,
    initKeySelection,
    resetSelection,
    itemRefs,
    onClick: onSelectClick,
    onKeyDown: onSelectKeyDown,
} = useSelectedItems<DCESummary, typeof ContentItem>({
    scopeKey: computed(() => String(dsc.value?.id ?? "")),
    getItemKey: elementKey,
    allItems: collectionElements as never,
    selectable: computed(() => canEdit.value),
    expectedKeyDownClass: "content-item",
    // A collection listing has no filtering and no query selection, so these
    // are inert; they exist because the composable is shared with the history
    // panel, where filtering drives select-all-in-query.
    filterText: ref(""),
    totalItemsInQuery: computed(() => collectionElements.value.length),
    filterClass: HistoryFilters,
    // Deleting an element from a collection is not offered here.
    onDelete: () => {},
});

/** The datasets behind the selected elements, for the collection creator. */
const selectedDatasets = computed(() =>
    Array.from(selectedItems.value.values())
        .filter((element) => element.element_type === "hda")
        .map((element) => element.object as HistoryItemSummary),
);

async function updateDsc(collection: CollectionEntry, fields: Object | undefined) {
    if (!isHDCA(collection)) {
        return;
    }
    const updatedCollection = await updateContentFields(collection, fields);
    // Update only editable fields
    collection.name = updatedCollection.name || collection.name;
    collection.tags = updatedCollection.tags || collection.tags;
}

function getItemKey(item: DCESummary) {
    return `${item.element_type}-${item.id}`;
}

function onScroll(newOffset: number) {
    offset.value = newOffset;
}

async function onViewDatasetCollectionElement(element: DCESummary) {
    if (!isCollectionElement(element)) {
        return;
    }
    offset.value = 0;
    const collection: SubCollection = {
        ...element.object,
        name: element.element_identifier,
        hdca_id: rootCollection.value.id,
    };
    emit("view-collection", collection);
}

watch(
    () => props.history,
    (newHistory, oldHistory) => {
        if (newHistory.id != oldHistory.id) {
            // Send up event closing out selected collection on history change.
            emit("update:selected-collections", []);
        }
    },
);

watch(
    jobState,
    () => {
        collectionElementsStore.invalidateCollectionElements(dsc.value);
        collectionElementsStore.fetchMissingElements(dsc.value, offset.value);
    },
    { deep: true },
);
</script>

<template>
    <Alert v-if="error" variant="error">
        {{ errorMessageAsString(error) }}
    </Alert>
    <ExpandedItems v-else v-slot="{ isExpanded, setExpanded }" :scope-key="dsc.id" :get-item-key="getItemKey">
        <section class="dataset-collection-panel w-100 d-flex flex-column" :class="{ 'compact-panel': multiView }">
            <section>
                <CollectionNavigation
                    :history-name="history.name"
                    :selected-collections="selectedCollections"
                    v-on="$listeners" />
                <CollectionDetails :dsc="dsc" :writeable="canEdit" @update:dsc="updateDsc(dsc, $event)" />
                <CollectionOperations v-if="canEdit && showControls" :dsc="dsc" />
            </section>
            <section class="position-relative flex-grow-1 scroller">
                <div>
                    <div v-if="canEdit" class="d-flex align-items-center p-2">
                        <GButton size="small" transparent @click="setShowSelection(!showSelection)">
                            {{ showSelection ? "Cancel" : "Select" }}
                        </GButton>
                        <template v-if="showSelection && selectionSize">
                            <span class="mx-2">{{ selectionSize }} selected</span>
                            <GButton size="small" color="blue" @click="showCollectionCreator = true">
                                Build Dataset List
                            </GButton>
                        </template>
                    </div>

                    <b-alert
                        v-if="collectionElements.length === 0"
                        class="m-2"
                        :variant="populatedStateMsg ? 'danger' : 'info'"
                        show>
                        {{ populatedStateMsg || "This is an empty collection." }}
                    </b-alert>
                    <ListingLayout
                        v-else
                        data-key="element_index"
                        :items="collectionElements"
                        :loading="loading"
                        @scroll="onScroll">
                        <template v-slot:item="{ item }">
                            <ContentItem
                                v-if="item.id === undefined"
                                :id="item.element_index + 1"
                                :item="item"
                                :is-placeholder="true"
                                name="Loading..." />
                            <ContentItem
                                v-else
                                :id="item.element_index + 1"
                                :ref="itemRefs[elementKey(item)]"
                                :item="item.object"
                                :name="item.element_identifier"
                                :expand-dataset="isExpanded(item)"
                                :is-dataset="item.element_type == 'hda'"
                                :taggable="item.element_type == 'hda'"
                                :selectable="showSelection && item.element_type == 'hda'"
                                :selected="isSelected(item)"
                                :is-range-select-anchor="isRangeSelectAnchor(item)"
                                :select-click-handler="onSelectClick"
                                :filterable="filterable"
                                @update:selected="setSelected(item, $event)"
                                @init-key-selection="initKeySelection"
                                @on-key-down="onSelectKeyDown(item, $event)"
                                @drag-start="setItemDragstart(item, $event)"
                                @update:expand-dataset="setExpanded(item, $event)"
                                @view-collection="onViewDatasetCollectionElement(item)" />
                        </template>
                    </ListingLayout>

                    <CollectionCreatorIndex
                        v-if="showCollectionCreator"
                        :history-id="history.id"
                        collection-type="list"
                        :extended-collection-type="{}"
                        :selected-items="selectedDatasets"
                        :show.sync="showCollectionCreator"
                        hide-on-create
                        default-hide-source-items
                        @created-collection="onCreatedCollection" />
                </div>
            </section>
        </section>
    </ExpandedItems>
</template>

<style scoped>
.compact-panel {
    max-width: 15rem;
}
</style>
