<script setup lang="ts">
import { faCheckCircle, faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BLink, BModal } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { HDASummary, HistoryItemSummary, HistorySummary } from "@/api";
import { createDatasetCollection } from "@/components/History/model/queries";
import { useCollectionBuilderItemsStore } from "@/stores/collectionBuilderItemsStore";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";
import { orList } from "@/utils/strings";

import type { CollectionType, DatasetPair } from "../History/adapters/buildCollectionModal";

import ListCollectionCreator from "./ListCollectionCreator.vue";
import PairCollectionCreator from "./PairCollectionCreator.vue";
import PairedListCollectionCreator from "./PairedListCollectionCreator.vue";
import Heading from "@/components/Common/Heading.vue";
import GenericItem from "@/components/History/Content/GenericItem.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    historyId: string;
    showModal: boolean;
    collectionType: CollectionType;
    selectedItems?: HistoryItemSummary[];
    defaultHideSourceItems?: boolean;
    extensions?: string[];
    fromRulesInput?: boolean;
    hideModalOnCreate?: boolean;
    filterText?: string;
}
const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "created-collection", collection: any): void;
    (e: "update:show-modal", showModal: boolean): void;
}>();

/** Computed toggle that handles opening and closing the modal */
const localShowToggle = computed({
    get: () => props.showModal,
    set: (value: boolean) => {
        emit("update:show-modal", value);
    },
});

// Create Collection refs
const creatingCollection = ref(false);
const createCollectionError = ref<string | null>(null);
const createdCollection = ref<any>(null);

// History items variables
const historyItemsError = ref<string | null>(null);
const collectionItemsStore = useCollectionBuilderItemsStore();
const historyStore = useHistoryStore();
const history = computed(() => historyStore.getHistoryById(props.historyId));
const historyId = computed(() => props.historyId);
const localFilterText = computed(() => props.filterText || "");
const historyUpdateTime = computed(() => history.value?.update_time);
const isFetchingItems = computed(() => collectionItemsStore.isFetching[localFilterText.value]);
const historyDatasets = computed(() => {
    if (collectionItemsStore.cachedDatasetsForFilterText) {
        return collectionItemsStore.cachedDatasetsForFilterText[localFilterText.value] || [];
    } else {
        return [];
    }
});

/** Flag for the initial fetch of history items */
const initialFetch = ref(false);

/** Whether a list of items was selected to create a collection from */
const fromSelection = computed(() => !!props.selectedItems?.length);

/** Items to create the collection from */
const creatorItems = computed(() => (fromSelection.value ? props.selectedItems : historyDatasets.value));

watch(
    () => localShowToggle.value,
    async (show) => {
        if (show) {
            await fetchHistoryDatasets();
            if (!initialFetch.value) {
                initialFetch.value = true;
            }
        }
    },
    { immediate: true }
);

// Fetch items when history ID or update time changes, only if localShowToggle is true
watch([historyId, historyUpdateTime, localFilterText], async () => {
    if (localShowToggle.value) {
        await fetchHistoryDatasets();
    }
});

// If there is a change in `historyDatasets`, but we have selected items, we should update the selected items
watch(
    () => historyDatasets.value,
    (newDatasets) => {
        if (fromSelection.value) {
            // find each selected item in the new datasets, and update it
            props.selectedItems?.forEach((selectedItem) => {
                const newDataset = newDatasets.find((dataset) => dataset.id === selectedItem.id);
                if (newDataset) {
                    Object.assign(selectedItem, newDataset);
                }
            });
        }
    }
);

const extensionInTitle = computed<string>(() => {
    const extensions = props.extensions;
    if (!extensions || extensions.length == 0 || extensions.indexOf("data") >= 0) {
        return "";
    } else {
        return orList(extensions);
    }
});

const modalTitle = computed(() => {
    if (props.collectionType === "list") {
        return localize(`Create a list of ${fromSelection.value ? "selected" : ""} ${extensionInTitle.value} datasets`);
    } else if (props.collectionType === "list:paired") {
        return localize(
            `Create a list of ${fromSelection.value ? "selected" : ""} ${extensionInTitle.value} paired datasets`
        );
    } else if (props.collectionType === "paired") {
        return localize(
            `Create a ${extensionInTitle.value} paired dataset collection ${
                fromSelection.value ? "from selected items" : ""
            }`
        );
    } else {
        return localize("Create a collection");
    }
});

// Methods
function createListCollection(elements: HDASummary[], name: string, hideSourceItems: boolean) {
    const returnedElems = elements.map((element) => ({
        id: element.id,
        name: element.name,
        //TODO: this allows for list:list even if the implementation does not - reconcile
        src: "src" in element ? element.src : element.history_content_type == "dataset" ? "hda" : "hdca",
    }));
    return createHDCA(returnedElems, "list", name, hideSourceItems);
}

function createListPairedCollection(elements: DatasetPair[], name: string, hideSourceItems: boolean) {
    const returnedElems = elements.map((pair) => ({
        collection_type: "paired",
        src: "new_collection",
        name: pair.name,
        element_identifiers: [
            {
                name: "forward",
                id: pair.forward.id,
                src: "src" in pair.forward ? pair.forward.src : "hda",
            },
            {
                name: "reverse",
                id: pair.reverse.id,
                src: "src" in pair.reverse ? pair.reverse.src : "hda",
            },
        ],
    }));
    return createHDCA(returnedElems, "list:paired", name, hideSourceItems);
}

function createPairedCollection(elements: DatasetPair, name: string, hideSourceItems: boolean) {
    const { forward, reverse } = elements;
    const returnedElems = [
        { name: "forward", src: "src" in forward ? forward.src : "hda", id: forward.id },
        { name: "reverse", src: "src" in reverse ? reverse.src : "hda", id: reverse.id },
    ];
    return createHDCA(returnedElems, "paired", name, hideSourceItems);
}

async function createHDCA(
    element_identifiers: any[],
    collection_type: CollectionType,
    name: string,
    hide_source_items: boolean,
    options = {}
) {
    try {
        creatingCollection.value = true;
        const collection = await createDatasetCollection(history.value as HistorySummary, {
            collection_type,
            name,
            hide_source_items,
            element_identifiers,
            options,
        });

        emit("created-collection", collection);
        createdCollection.value = collection;

        if (props.hideModalOnCreate) {
            hideModal();
        }
    } catch (error) {
        createCollectionError.value = error as string;
    } finally {
        creatingCollection.value = false;
    }
}

async function fetchHistoryDatasets() {
    const { error } = await collectionItemsStore.fetchDatasetsForFiltertext(
        historyId.value,
        historyUpdateTime.value,
        localFilterText.value
    );
    if (error) {
        historyItemsError.value = error;
        console.error("Error fetching history items:", historyItemsError.value);
    } else {
        historyItemsError.value = null;
    }
}

function hideModal() {
    localShowToggle.value = false;
}

function resetModal() {
    createCollectionError.value = null;
    createdCollection.value = null;
}
</script>

<template>
    <BModal
        id="collection-creator-modal"
        v-model="localShowToggle"
        :busy="(fromSelection && isFetchingItems) || creatingCollection"
        modal-class="ui-modal collection-creator-modal"
        :hide-footer="!createdCollection && !createCollectionError"
        :ok-disabled="!!createdCollection || !!createCollectionError"
        :cancel-title="localize('Exit')"
        footer-class="d-flex justify-content-between"
        :ok-title="localize('Create Collection')"
        @hidden="resetModal">
        <template v-slot:modal-header>
            <Heading class="w-100" size="sm">
                <div class="d-flex justify-content-between unselectable w-100">
                    <div>{{ modalTitle }}</div>
                    <div v-if="!!history">
                        From history: <b>{{ history.name }}</b>
                    </div>
                </div>
            </Heading>
        </template>
        <BAlert v-if="isFetchingItems && !initialFetch" variant="info" show>
            <LoadingSpan :message="localize('Loading items')" />
        </BAlert>
        <BAlert v-else-if="!fromSelection && historyItemsError" variant="danger" show>
            {{ historyItemsError }}
        </BAlert>
        <BAlert v-else-if="creatingCollection" variant="info" show>
            <LoadingSpan :message="localize('Creating collection')" />
        </BAlert>
        <BAlert v-else-if="createCollectionError" variant="danger" show>
            {{ createCollectionError }}
            <BLink class="text-decoration-none" @click.stop.prevent="resetModal">
                <FontAwesomeIcon :icon="faUndo" fixed-width />
                {{ localize("Try again") }}
            </BLink>
        </BAlert>
        <div v-else-if="createdCollection">
            <BAlert variant="success" show>
                <FontAwesomeIcon :icon="faCheckCircle" class="text-success" fixed-width />
                {{ localize("Collection created successfully.") }}
                <BLink v-if="!fromSelection" class="text-decoration-none" @click.stop.prevent="resetModal">
                    <FontAwesomeIcon :icon="faUndo" fixed-width />
                    {{ localize("Create another collection") }}
                </BLink>
            </BAlert>

            <!-- TODO: This is a bit shady, better if we confirm it is a collection type -->
            <GenericItem :item-id="createdCollection.id" item-src="hdca" />
        </div>
        <ListCollectionCreator
            v-else-if="props.collectionType === 'list'"
            :history-id="props.historyId"
            :initial-elements="creatorItems || []"
            :default-hide-source-items="props.defaultHideSourceItems"
            :from-selection="fromSelection"
            :extensions="props.extensions"
            @clicked-create="createListCollection"
            @on-cancel="hideModal" />
        <PairedListCollectionCreator
            v-else-if="props.collectionType === 'list:paired'"
            :history-id="props.historyId"
            :initial-elements="creatorItems || []"
            :default-hide-source-items="props.defaultHideSourceItems"
            :from-selection="fromSelection"
            :extensions="props.extensions"
            @clicked-create="createListPairedCollection"
            @on-cancel="hideModal" />
        <PairCollectionCreator
            v-else-if="props.collectionType === 'paired'"
            :history-id="props.historyId"
            :initial-elements="creatorItems || []"
            :default-hide-source-items="props.defaultHideSourceItems"
            :from-selection="fromSelection"
            :extensions="props.extensions"
            @clicked-create="createPairedCollection"
            @on-cancel="hideModal" />
    </BModal>
</template>

<style lang="scss">
/** NOTE: Not using `<style scoped> here because these classes are
`BModal` `body-class` and `content-class` and don't seem to work
with scoped */
.collection-creator-modal {
    .modal-dialog {
        width: 85%;
        max-width: 100%;
    }
}
</style>
