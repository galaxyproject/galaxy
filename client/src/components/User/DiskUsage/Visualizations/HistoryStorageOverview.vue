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
    console.log(activeVsDeletedTotalSizeData.value);
});

function buildTopTenDatasetsBySizeData(datasetsSizeSummary: ItemSizeSummary[]): DataValuePoint[] {
    const topTenDatasetsBySize = datasetsSizeSummary.sort((a, b) => b.size - a.size).slice(0, 10);
    return topTenDatasetsBySize.map((dataset, index) => ({
        index,
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
            index: 0,
            id: "active",
            label: "Active",
            value: activeDatasetsSize,
        },
        {
            index: 1,
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
            <b>{{ props.historyId }}</b>
        </p>
        <p class="text-center mx-3">
            These graphs include <b>deleted datasets</b>. Even if you delete datasets, they still take up storage space
            until you permanently delete them. However, you can recover the storage space by permanently deleting them
            from the <i>Discarded Items</i> section of the
            <router-link :to="{ name: 'StorageManager' }"><b>Storage Manager</b></router-link> page.
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
