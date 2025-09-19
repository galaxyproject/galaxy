<script setup lang="ts">
import { faCheckCircle, faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BLink, BModal } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { type CreateNewCollectionPayload, type HDCASummary, type HistoryItemSummary, isHDCA } from "@/api";
import { createHistoryDatasetCollectionInstanceFull, type SampleSheetCollectionType } from "@/api/datasetCollections";
import type { ExtendedCollectionType } from "@/components/Form/Elements/FormData/types";
import { useCollectionBuilderItemsStore } from "@/stores/collectionBuilderItemsStore";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";
import { orList } from "@/utils/strings";
import { stateIsTerminal } from "@/utils/utils";

import type { CollectionBuilderType } from "../History/adapters/buildCollectionModal";
import type { SupportedPairedOrPairedBuilderCollectionTypes } from "./common/useCollectionCreator";

import ListCollectionCreator from "./ListCollectionCreator.vue";
import PairCollectionCreator from "./PairCollectionCreator.vue";
import PairedOrUnpairedListCollectionCreator from "./PairedOrUnpairedListCollectionCreator.vue";
import SampleSheetCollectionCreator from "./SampleSheetCollectionCreator.vue";
import Heading from "@/components/Common/Heading.vue";
import GenericItem from "@/components/History/Content/GenericItem.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    historyId: string;
    show: boolean;
    collectionType: CollectionBuilderType;
    extendedCollectionType: ExtendedCollectionType;
    selectedItems?: HistoryItemSummary[];
    defaultHideSourceItems?: boolean;
    extensions?: string[];
    fromRulesInput?: boolean;
    hideOnCreate?: boolean;
    filterText?: string;
    notModal?: boolean;
    suggestedName?: string;
    useBetaComponents?: boolean;
}
const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "created-collection", collection: HDCASummary): void;
    (e: "update:show", show: boolean): void;
    (e: "on-hide"): void;
}>();

/** Computed toggle that handles showing and hiding the creator */
const localShowToggle = computed({
    get: () => props.show,
    set: (value: boolean) => {
        emit("update:show", value);
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
const pairedOrUnpairedSupportedCollectionType = computed<SupportedPairedOrPairedBuilderCollectionTypes | null>(() => {
    if (
        ["list:paired", "list:list", "list:paired_or_unpaired", "list:list:paired"].indexOf(props.collectionType) !== -1
    ) {
        return props.collectionType as SupportedPairedOrPairedBuilderCollectionTypes;
    } else {
        return null;
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
    { immediate: true },
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
    },
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
            `Create a list of ${fromSelection.value ? "selected" : ""} ${extensionInTitle.value} paired datasets`,
        );
    } else if (props.collectionType === "paired") {
        return localize(
            `Create a ${extensionInTitle.value} paired dataset collection ${
                fromSelection.value ? "from selected items" : ""
            }`,
        );
    } else {
        return localize("Create a collection");
    }
});

const historyItemsStore = useHistoryItemsStore();
/** The created collection accessed from the history items store */
const createdCollectionInHistory = computed<HDCASummary | undefined>(() => {
    const historyItems = historyItemsStore.getHistoryItems(props.historyId, "");
    const createdCollectionItem = historyItems.find((item) => item.id === createdCollection.value?.id);
    if (createdCollectionItem && isHDCA(createdCollectionItem)) {
        return createdCollectionItem;
    }
    return undefined;
});
/** If the created collection has achieved a terminal state */
const createdCollectionInReadyState = computed(
    () => createdCollectionInHistory.value && stateIsTerminal(createdCollectionInHistory.value),
);

// Methods

async function createHDCA(payload: CreateNewCollectionPayload) {
    try {
        creatingCollection.value = true;
        const collection = await createHistoryDatasetCollectionInstanceFull(payload);
        emit("created-collection", collection);
        createdCollection.value = collection;

        if (props.hideOnCreate) {
            hideCreator();
        }
    } catch (error) {
        createCollectionError.value = error as string;
    } finally {
        creatingCollection.value = false;
    }
}

watch(
    () => createdCollectionInReadyState.value,
    (stateReady) => {
        if (stateReady && createdCollectionInHistory.value) {
            emit("created-collection", createdCollectionInHistory.value);
        }
    },
);

async function fetchHistoryDatasets() {
    const { error } = await collectionItemsStore.fetchDatasetsForFiltertext(
        historyId.value,
        historyUpdateTime.value,
        localFilterText.value,
    );
    if (error) {
        historyItemsError.value = error;
        console.error("Error fetching history items:", historyItemsError.value);
    } else {
        historyItemsError.value = null;
    }
}

function hideCreator() {
    localShowToggle.value = false;
    emit("on-hide");
}

function resetCreator() {
    createCollectionError.value = null;
    createdCollection.value = null;
}

const creator = ref();

function redrawCreator() {
    if (creator.value) {
        creator.value.redraw();
    }
}

const sampleSheetType = computed<SampleSheetCollectionType | null>(() => {
    if (!props.collectionType.startsWith("sample_sheet")) {
        return null;
    }
    return props.collectionType as SampleSheetCollectionType;
});

defineExpose({ redrawCreator });
</script>

<template>
    <component
        :is="props.notModal ? 'div' : BModal"
        id="collection-creator-modal"
        v-model="localShowToggle"
        :busy="(fromSelection && isFetchingItems) || creatingCollection"
        modal-class="ui-modal collection-creator-modal"
        :hide-footer="!createdCollection && !createCollectionError"
        ok-only
        :ok-title="localize('Exit')"
        ok-variant="secondary"
        @hidden="resetCreator">
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
            <BLink class="text-decoration-none" @click.stop.prevent="resetCreator">
                <FontAwesomeIcon :icon="faUndo" fixed-width />
                {{ localize("Try again") }}
            </BLink>
        </BAlert>
        <div v-else-if="createdCollection">
            <BAlert v-if="!createdCollectionInReadyState" variant="info" show>
                <LoadingSpan :message="localize('Waiting for collection to be ready')" />
            </BAlert>
            <template v-else>
                <BAlert variant="success" show>
                    <FontAwesomeIcon :icon="faCheckCircle" class="text-success" fixed-width />
                    {{ localize("Collection created successfully.") }}
                    {{ localize("It might still not be a valid input based on individual element properties.") }}
                    {{ localize("Expand the collection to see its individual elements.") }}
                    <BLink v-if="!fromSelection" class="text-decoration-none" @click.stop.prevent="resetCreator">
                        <FontAwesomeIcon :icon="faUndo" fixed-width />
                        {{ localize("Create another collection") }}
                    </BLink>
                </BAlert>

                <GenericItem
                    v-if="createdCollection.history_content_type === 'dataset_collection'"
                    :item-id="createdCollection.id"
                    item-src="hdca" />
            </template>
        </div>
        <ListCollectionCreator
            v-else-if="props.collectionType === 'list'"
            :history-id="props.historyId"
            :initial-elements="creatorItems || []"
            :default-hide-source-items="props.defaultHideSourceItems"
            :from-selection="fromSelection"
            :extensions="props.extensions"
            :suggested-name="props.suggestedName"
            mode="modal"
            @on-create="createHDCA"
            @on-cancel="hideCreator" />
        <PairedOrUnpairedListCollectionCreator
            v-else-if="pairedOrUnpairedSupportedCollectionType"
            ref="creator"
            :history-id="props.historyId"
            :initial-elements="creatorItems || []"
            :default-hide-source-items="props.defaultHideSourceItems"
            :from-selection="fromSelection"
            :extensions="props.extensions"
            :suggested-name="props.suggestedName"
            :collection-type="pairedOrUnpairedSupportedCollectionType"
            mode="modal"
            @on-create="createHDCA"
            @on-cancel="hideCreator" />
        <PairCollectionCreator
            v-else-if="props.collectionType === 'paired'"
            :history-id="props.historyId"
            :initial-elements="creatorItems || []"
            :default-hide-source-items="props.defaultHideSourceItems"
            :from-selection="fromSelection"
            :extensions="props.extensions"
            :suggested-name="props.suggestedName"
            mode="modal"
            @on-cancel="hideCreator"
            @on-create="createHDCA" />
        <SampleSheetCollectionCreator
            v-else-if="sampleSheetType"
            :history-id="props.historyId"
            :initial-elements="creatorItems || []"
            :default-hide-source-items="props.defaultHideSourceItems"
            :from-selection="fromSelection"
            :extensions="props.extensions"
            :collection-type="sampleSheetType"
            :extended-collection-type="extendedCollectionType"
            @on-create="createHDCA"
            @on-cancel="hideCreator" />
    </component>
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
