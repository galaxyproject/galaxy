<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BForm, BFormGroup, BFormSelect, BInputGroup } from "bootstrap-vue";
import { computed, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { useSelectableObjectStores } from "@/composables/useObjectStores";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";

import type { DataValuePoint } from "./Charts";
import { fetchHistoryContentsSizeSummary, type ItemSizeSummary } from "./service";
import {
    buildTopNDatasetsBySizeData,
    byteFormattingForChart,
    useAdvancedFiltering,
    useDataLoading,
    useDatasetsToDisplay,
} from "./util";

import BarChart from "./Charts/BarChart.vue";
import OverviewPage from "./OverviewPage.vue";
import RecoverableItemSizeTooltip from "./RecoverableItemSizeTooltip.vue";
import SelectedItemActions from "./SelectedItemActions.vue";
import WarnDeletedDatasets from "./WarnDeletedDatasets.vue";
import FilterObjectStoreLink from "@/components/Common/FilterObjectStoreLink.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const router = useRouter();
const { getHistoryNameById, getHistoryById } = useHistoryStore();

interface Props {
    historyId: string;
}

const props = defineProps<Props>();

const activeVsDeletedTotalSizeData = ref<DataValuePoint[] | null>(null);
const {
    numberOfDatasetsToDisplayOptions,
    numberOfDatasetsToDisplay,
    numberOfDatasetsLimit,
    datasetsSizeSummaryMap,
    topNDatasetsBySizeData,
    isRecoverableDataPoint,
    onUndeleteDataset,
    onPermanentlyDeleteDataset,
} = useDatasetsToDisplay();

const { isLoading, loadDataOnMount } = useDataLoading();
const { isAdvanced, toggleAdvanced, inputGroupClasses, faAngleDoubleDown, faAngleDoubleUp } = useAdvancedFiltering();
const { selectableObjectStores, hasSelectableObjectStores } = useSelectableObjectStores();

const objectStore = ref<string>();

const canEditHistory = computed(() => {
    const history = getHistoryById(props.historyId);
    return (history && !history.purged && !history.archived) ?? false;
});

function onChangeObjectStore(value?: string) {
    objectStore.value = value;
    reloadDataFromServer();
}

async function reloadDataFromServer() {
    const allDatasetsInHistorySizeSummary = await fetchHistoryContentsSizeSummary(
        props.historyId,
        numberOfDatasetsLimit,
        objectStore.value
    );
    datasetsSizeSummaryMap.clear();
    allDatasetsInHistorySizeSummary.forEach((dataset) => datasetsSizeSummaryMap.set(dataset.id, dataset));

    buildGraphsData();
}

loadDataOnMount(reloadDataFromServer);

function buildGraphsData() {
    const allDatasetsInHistorySizeSummary = Array.from(datasetsSizeSummaryMap.values());
    topNDatasetsBySizeData.value = buildTopNDatasetsBySizeData(
        allDatasetsInHistorySizeSummary,
        numberOfDatasetsToDisplay.value
    );
    activeVsDeletedTotalSizeData.value = buildActiveVsDeletedTotalSizeData(allDatasetsInHistorySizeSummary);
}

function buildActiveVsDeletedTotalSizeData(datasetsSizeSummary: ItemSizeSummary[]): DataValuePoint[] {
    const activeDatasetsSize = datasetsSizeSummary
        .filter((dataset) => !dataset.deleted)
        .reduce((total, dataset) => total + dataset.size, 0);
    const deletedDatasetsSize = datasetsSizeSummary
        .filter((dataset) => dataset.deleted)
        .reduce((total, dataset) => total + dataset.size, 0);
    return [
        {
            id: "active",
            label: "Active",
            value: activeDatasetsSize,
        },
        {
            id: "deleted",
            label: "Deleted",
            value: deletedDatasetsSize,
        },
    ];
}

async function onViewDataset(datasetId: string) {
    router.push({
        name: "DatasetDetails",
        params: {
            historyId: props.historyId,
            datasetId: datasetId,
        },
    });
}

function onPermDelete(datasetId: string) {
    onPermanentlyDeleteDataset(buildGraphsData, datasetId);
}

function onUndelete(datasetId: string) {
    onUndeleteDataset(buildGraphsData, datasetId);
}
</script>
<template>
    <OverviewPage class="history-storage-overview" title="History Storage Overview">
        <p class="text-justify">
            Here you will find some Graphs displaying the storage taken by datasets in your history:
            <b>{{ getHistoryNameById(props.historyId) }}</b
            >. You can use these graphs to identify the datasets that take the most space in your history. You can also
            go to the
            <router-link :to="{ name: 'HistoriesOverview' }"><b>Histories Storage Overview</b></router-link> page to see
            the storage taken by <b>all your histories</b>.
        </p>
        <WarnDeletedDatasets />
        <div v-if="isLoading" class="text-center">
            <LoadingSpan class="mt-5" :message="localize('Loading your storage data. This may take a while...')" />
        </div>
        <div v-else>
            <BarChart
                v-if="topNDatasetsBySizeData"
                :description="
                    localize(
                        `These are the ${numberOfDatasetsToDisplay} datasets that take the most space in this history. Click on a bar to see more information about the dataset.`
                    )
                "
                :data="topNDatasetsBySizeData"
                :enable-selection="true"
                v-bind="byteFormattingForChart">
                <template v-slot:title>
                    <b>{{ localize(`Top ${numberOfDatasetsToDisplay} Datasets by Size`) }}</b>
                    <BInputGroup size="sm" :class="inputGroupClasses">
                        <BFormSelect
                            v-if="!isAdvanced"
                            v-model="numberOfDatasetsToDisplay"
                            :options="numberOfDatasetsToDisplayOptions"
                            :disabled="isLoading"
                            title="Number of histories to show"
                            size="sm"
                            @change="buildGraphsData()">
                        </BFormSelect>
                        <BButton
                            v-b-tooltip.hover.bottom.noninteractive
                            aria-haspopup="true"
                            size="sm"
                            title="Toggle Advanced Filtering"
                            data-description="wide toggle advanced filter"
                            @click="toggleAdvanced">
                            <FontAwesomeIcon :icon="isAdvanced ? faAngleDoubleUp : faAngleDoubleDown" />
                        </BButton>
                    </BInputGroup>
                </template>
                <template v-slot:options>
                    <div v-if="isAdvanced" class="clear-fix">
                        <BForm>
                            <BFormGroup
                                id="input-group-num-histories"
                                label="Number of histories:"
                                label-for="input-num-histories"
                                description="This is the maximum number of histories that will be displayed.">
                                <BFormSelect
                                    v-model="numberOfDatasetsToDisplay"
                                    :options="numberOfDatasetsToDisplayOptions"
                                    :disabled="isLoading"
                                    title="Number of histories to show"
                                    @change="buildGraphsData()">
                                </BFormSelect>
                            </BFormGroup>
                            <BFormGroup
                                v-if="selectableObjectStores && hasSelectableObjectStores"
                                id="input-group-object-store"
                                label="Storage location:"
                                label-for="input-object-store"
                                description="This will constrain history size calculations to a particular storage location.">
                                <FilterObjectStoreLink
                                    :object-stores="selectableObjectStores"
                                    :value="objectStore"
                                    @change="onChangeObjectStore" />
                            </BFormGroup>
                        </BForm>
                    </div>
                </template>
                <template v-slot:tooltip="{ data }">
                    <RecoverableItemSizeTooltip
                        v-if="data"
                        :data="data"
                        :is-recoverable="isRecoverableDataPoint(data)" />
                </template>
                <template v-slot:selection="{ data }">
                    <SelectedItemActions
                        :data="data"
                        item-type="dataset"
                        :is-recoverable="isRecoverableDataPoint(data)"
                        :can-edit="canEditHistory"
                        @view-item="onViewDataset"
                        @undelete-item="onUndelete"
                        @permanently-delete-item="onPermDelete" />
                </template>
            </BarChart>

            <BarChart
                v-if="activeVsDeletedTotalSizeData"
                :title="localize('Active vs Deleted Total Size')"
                :description="
                    localize(
                        'This graph shows the total size of your datasets in this history, split between active and deleted datasets.'
                    )
                "
                :data="activeVsDeletedTotalSizeData"
                v-bind="byteFormattingForChart">
                <template v-slot:tooltip="{ data }">
                    <RecoverableItemSizeTooltip
                        v-if="data"
                        :data="data"
                        :is-recoverable="isRecoverableDataPoint(data)" />
                </template>
            </BarChart>
        </div>
    </OverviewPage>
</template>
