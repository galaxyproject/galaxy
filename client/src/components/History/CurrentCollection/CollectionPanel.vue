<!-- When a dataset collection is being viewed, this panel shows the contents of that collection -->

<script setup lang="ts">
import { computed, ref, watch } from "vue";

import ExpandedItems from "@/components/History/Content/ExpandedItems";
import { updateContentFields } from "@/components/History/model/queries";
import { useCollectionElementsStore } from "@/stores/collectionElementsStore";
import { HistorySummary } from "@/stores/historyStore";
import { DCESummary, HDCASummary } from "@/stores/services";

import CollectionDetails from "./CollectionDetails.vue";
import CollectionNavigation from "./CollectionNavigation.vue";
import CollectionOperations from "./CollectionOperations.vue";
import ContentItem from "@/components/History/Content/ContentItem.vue";
import ListingLayout from "@/components/History/Layout/ListingLayout.vue";

interface Props {
    history: HistorySummary;
    selectedCollections: HDCASummary[];
    showControls?: boolean;
    filterable?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    showControls: true,
    filterable: false,
});

const collectionElementsStore = useCollectionElementsStore();

const emit = defineEmits<{
    (e: "view-collection", collection: HDCASummary): void;
    (e: "update:selected-collections", collections: HDCASummary[]): void;
}>();

const offset = ref(0);

const dsc = computed(() => props.selectedCollections[props.selectedCollections.length - 1] as HDCASummary);
const collectionElements = computed(() => collectionElementsStore.getCollectionElements(dsc.value, offset.value));
const loading = computed(() => collectionElementsStore.isLoadingCollectionElements(dsc.value));
const jobState = computed(() => dsc.value?.job_state_summary);
const rootCollection = computed(() => props.selectedCollections[0]);
const isRoot = computed(() => dsc.value == rootCollection.value);

function updateDsc(collection: any, fields: Object | undefined) {
    updateContentFields(collection, fields).then((response) => {
        Object.keys(response).forEach((key) => {
            collection[key] = response[key];
        });
    });
}

function getItemKey(item: DCESummary) {
    return item.id;
}

function onScroll(newOffset: number) {
    offset.value = newOffset;
}

/**
 * Passes a sub-collection i.e a collection element object containing another collection, into
 * a populated object for drill-down without the need for a separate data request. This object
 * is used for breadcrumbs in the navigation component and to render the collection details and
 * description at the top of the collection panel. Details include the collection name, the
 * collection type, and the element count.
 */
function onViewSubCollection(itemObject: HDCASummary, elementIdentifier: string) {
    const collectionObject = {
        name: elementIdentifier,
        ...itemObject,
    };
    emit("view-collection", collectionObject);
}

watch(
    () => props.history,
    (newHistory, oldHistory) => {
        if (newHistory.id != oldHistory.id) {
            // Send up event closing out selected collection on history change.
            emit("update:selected-collections", []);
        }
    }
);

watch(
    jobState,
    () => {
        collectionElementsStore.loadCollectionElements(dsc.value);
    },
    { deep: true }
);
</script>

<template>
    <ExpandedItems v-slot="{ isExpanded, setExpanded }" :scope-key="dsc.id" :get-item-key="getItemKey">
        <section class="dataset-collection-panel w-100 d-flex flex-column">
            <section>
                <CollectionNavigation
                    :history-name="history.name"
                    :selected-collections="selectedCollections"
                    v-on="$listeners" />
                <CollectionDetails :dsc="dsc" :writeable="isRoot" @update:dsc="updateDsc(dsc, $event)" />
                <CollectionOperations v-if="isRoot && showControls" :dsc="dsc" />
            </section>
            <section class="position-relative flex-grow-1 scroller">
                <div>
                    <ListingLayout :items="collectionElements" :loading="loading" @scroll="onScroll">
                        <template v-slot:item="{ item }">
                            <ContentItem
                                :id="item.element_index + 1"
                                :item="item.object"
                                :name="item.element_identifier"
                                :expand-dataset="isExpanded(item)"
                                :is-dataset="item.element_type == 'hda'"
                                :filterable="filterable"
                                @update:expand-dataset="setExpanded(item, $event)"
                                @view-collection="onViewSubCollection" />
                        </template>
                    </ListingLayout>
                </div>
            </section>
        </section>
    </ExpandedItems>
</template>
