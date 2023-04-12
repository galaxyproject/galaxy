<script setup lang="ts">
import localize from "@/utils/localization";
import type { DataValuePoint } from "./Charts";
import { ref, onMounted } from "vue";
import PieChart from "./Charts/PieChart.vue";
import { bytesLabelFormatter } from "./Charts/utils";
import { getHistoryContentsSizeSummary, type ItemSizeSummary } from "./service";
import RecoverableItemSizeTooltip from "./RecoverableItemSizeTooltip.vue";

const props = defineProps({
    historyId: {
        type: String,
        required: true,
    },
});

const datasetsSizeSummaryMap = new Map<string, ItemSizeSummary>();
const topTenDatasetsBySizeData = ref<DataValuePoint[] | null>(null);
const activeVsDeletedTotalSizeData = ref<DataValuePoint[] | null>(null);

onMounted(async () => {
    const allDatasetsInHistorySizeSummary = await getHistoryContentsSizeSummary(props.historyId);
    allDatasetsInHistorySizeSummary.forEach((dataset) => datasetsSizeSummaryMap.set(dataset.id, dataset));

    topTenDatasetsBySizeData.value = buildTopTenDatasetsBySizeData(allDatasetsInHistorySizeSummary);
    activeVsDeletedTotalSizeData.value = buildActiveVsDeletedTotalSizeData(allDatasetsInHistorySizeSummary);
});

function buildTopTenDatasetsBySizeData(datasetsSizeSummary: ItemSizeSummary[]): DataValuePoint[] {
    const topTenDatasetsBySize = datasetsSizeSummary.sort((a, b) => b.size - a.size).slice(0, 10);
    return topTenDatasetsBySize.map((dataset) => ({
        id: dataset.id,
        label: dataset.name,
        value: dataset.size,
    }));
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

function isRecoverableDataPoint(dataPoint?: DataValuePoint): boolean {
    if (dataPoint) {
        const historiesSizeSummary = datasetsSizeSummaryMap.get(dataPoint.id || "");
        return historiesSizeSummary?.deleted || dataPoint.id === "deleted";
    }
    return false;
}
</script>
<template>
    <div>
        <router-link :to="{ name: 'StorageDashboard' }">{{ localize("Back to Dashboard") }}</router-link>
        <h2 class="text-center my-3">
            <b>History Storage Overview</b>
        </h2>
        <p class="text-center">
            Here you will find some Graphs displaying the storage taken by datasets in your history:
            <b>{{ props.historyId }}</b
            >. You can use these graphs to identify the datasets that take the most space in your history. You can also
            go to the
            <router-link :to="{ name: 'HistoriesOverview' }"><b>Histories Storage Overview</b></router-link> page to see
            the storage taken by <b>all your histories</b>.
        </p>
        <p class="text-center mx-3">
            Note: these graphs include <b>deleted datasets</b>. Remember that, even if you delete datasets, they still
            take up storage space. However, you can free up the storage space by permanently deleting them from the
            <i>Discarded Items</i> section of the
            <router-link :to="{ name: 'StorageManager' }"><b>Storage Manager</b></router-link> page or by selecting them
            individually in the graph and clicking the <b>Permanently Delete</b> button.
        </p>

        <PieChart
            v-if="topTenDatasetsBySizeData"
            title="Top 10 Datasets by Size"
            description="These are the 10 datasets that take the most space in this history."
            :data="topTenDatasetsBySizeData"
            :label-formatter="bytesLabelFormatter">
            <template v-slot:tooltip="{ data }">
                <RecoverableItemSizeTooltip :data="data" :is-recoverable="isRecoverableDataPoint(data)" />
            </template>
        </PieChart>

        <PieChart
            v-if="activeVsDeletedTotalSizeData"
            title="Active vs Deleted Total Size"
            description="This graph shows the total size of your datasets in this history, separated by whether they are active or deleted."
            :data="activeVsDeletedTotalSizeData"
            :label-formatter="bytesLabelFormatter">
            <template v-slot:tooltip="{ data }">
                <RecoverableItemSizeTooltip :data="data" :is-recoverable="isRecoverableDataPoint(data)" />
            </template>
        </PieChart>
    </div>
</template>
