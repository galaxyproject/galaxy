<!-- When a dataset collection is being viewed, this panel shows the contents of that collection -->

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import {
    canMutateHistory,
    type CollectionEntry,
    type DCESummary,
    type HDCASummary,
    type HistorySummary,
    isCollectionElement,
    isHDCA,
    type SubCollection,
    userOwnsHistory,
} from "@/api";
import ExpandedItems from "@/components/History/Content/ExpandedItems";
import { updateContentFields } from "@/components/History/model/queries";
import { useCollectionElementsStore } from "@/stores/collectionElementsStore";
import { useUserStore } from "@/stores/userStore";
import { setItemDragstart } from "@/utils/setDrag";
import { errorMessageAsString } from "@/utils/simple-error";

import CollectionDetails from "./CollectionDetails.vue";
import CollectionNavigation from "./CollectionNavigation.vue";
import CollectionOperations from "./CollectionOperations.vue";
import Alert from "@/components/Alert.vue";
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

const collectionElementsStore = useCollectionElementsStore();
const { currentUser } = storeToRefs(useUserStore());

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
// Elements cached by a previous visit may be outdated, so refresh them when entering a collection.
watch(dsc, refreshCollectionElements, { immediate: true });
watch(offset, () => {
    collectionElementsStore.fetchMissingElements(dsc.value, offset.value);
});

const collectionElements = computed(() => collectionElementsStore.getCollectionElements(dsc.value) ?? []);
const loading = computed(() => collectionElementsStore.isLoadingCollectionElements(dsc.value));
const error = computed(() => collectionElementsStore.getLoadingCollectionElementsError(dsc.value));
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
const canEdit = computed(
    () => isRoot.value && canMutateHistory(props.history) && userOwnsHistory(currentUser.value, props.history),
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

function refreshCollectionElements() {
    collectionElementsStore.invalidateCollectionElements(dsc.value);
    collectionElementsStore.fetchMissingElements(dsc.value, offset.value);
}

// Changes whenever a job or dataset inside the root collection changes state, including those of nested collections,
// which carry no state of their own on the client. Compared as a string because the history watcher replaces these
// objects on every update, even when their contents are the same.
const rootCollectionStates = computed(() => {
    const root = rootCollection.value;
    return JSON.stringify([root.populated_state, root.element_count, root.elements_states, root.job_state_summary]);
});
watch(rootCollectionStates, refreshCollectionElements);
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
                                :filterable="filterable"
                                @drag-start="setItemDragstart(item, $event)"
                                @update:expand-dataset="setExpanded(item, $event)"
                                @view-collection="onViewDatasetCollectionElement(item)" />
                        </template>
                    </ListingLayout>
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
