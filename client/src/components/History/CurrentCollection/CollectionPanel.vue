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
import { updateContentFields } from "@/components/History/model/queries";
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

/** Datasets picked out of this collection, to build a new collection from.
 *
 * Selecting inside a collection previously was not possible at all: the only
 * route to a new collection was unhiding the elements in the history and
 * working with them there.
 */
const selectedElements = ref(new Map<string, HistoryItemSummary>());
const showCollectionCreator = ref(false);

const selectedCount = computed(() => selectedElements.value.size);
const selectedDatasets = computed(() => Array.from(selectedElements.value.values()));

function isElementSelected(element: { object?: { id?: string } }) {
    return element.object?.id !== undefined && selectedElements.value.has(element.object.id);
}

function setElementSelected(element: { element_type?: string; object?: HistoryItemSummary }, selected: boolean) {
    const id = element.object?.id;
    // Only datasets can go into a new list; nested collections are skipped.
    if (!id || element.element_type !== "hda") {
        return;
    }
    const next = new Map(selectedElements.value);
    if (selected) {
        next.set(id, element.object as HistoryItemSummary);
    } else {
        next.delete(id);
    }
    selectedElements.value = next;
}

function clearElementSelection() {
    selectedElements.value = new Map();
}

function onCreatedCollection() {
    clearElementSelection();
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
                    <b-alert
                        v-if="collectionElements.length === 0"
                        class="m-2"
                        :variant="populatedStateMsg ? 'danger' : 'info'"
                        show>
                        {{ populatedStateMsg || "This is an empty collection." }}
                    </b-alert>
                    <div v-if="selectedCount" class="d-flex align-items-center p-2 border-bottom">
                        <GButton size="small" transparent class="mr-2" @click="clearElementSelection">
                            {{ selectedCount }} selected
                        </GButton>
                        <GButton size="small" color="blue" @click="showCollectionCreator = true">
                            Build Dataset List
                        </GButton>
                    </div>

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
                                :item="item.object"
                                :name="item.element_identifier"
                                :expand-dataset="isExpanded(item)"
                                :is-dataset="item.element_type == 'hda'"
                                :taggable="item.element_type == 'hda'"
                                :selectable="canEdit && item.element_type == 'hda'"
                                :selected="isElementSelected(item)"
                                :filterable="filterable"
                                @update:selected="setElementSelected(item, $event)"
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
