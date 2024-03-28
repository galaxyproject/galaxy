<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router/composables";

import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";

import type { DataValuePoint } from "./Charts";
import { fetchHistoryContentsSizeSummary, type ItemSizeSummary } from "./service";
import { buildTopNDatasetsBySizeData, byteFormattingForChart, useDataLoading, useDatasetsToDisplay } from "./util";

import BarChart from "./Charts/BarChart.vue";
import OverviewPage from "./OverviewPage.vue";
import RecoverableItemSizeTooltip from "./RecoverableItemSizeTooltip.vue";
import SelectedItemActions from "./SelectedItemActions.vue";
import WarnDeletedDatasets from "./WarnDeletedDatasets.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const router = useRouter();
const { getHistoryNameById } = useHistoryStore();

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

loadDataOnMount(async () => {
    const allDatasetsInHistorySizeSummary = await fetchHistoryContentsSizeSummary(
        props.historyId,
        numberOfDatasetsLimit
    );
    allDatasetsInHistorySizeSummary.forEach((dataset) => datasetsSizeSummaryMap.set(dataset.id, dataset));

    buildGraphsData();
});

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
                    <b-form-select
                        v-model="numberOfDatasetsToDisplay"
                        :options="numberOfDatasetsToDisplayOptions"
                        :disabled="isLoading"
                        title="Number of datasets to show"
                        class="float-right w-auto"
                        size="sm"
                        @change="buildGraphsData()">
                    </b-form-select>
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
