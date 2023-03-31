<script setup lang="ts">
import { BLink } from "bootstrap-vue";
import localize from "@/utils/localization";
import type { DataValuePoint } from "./Charts";
import { ref, onMounted } from "vue";
import PieChart from "./Charts/PieChart.vue";
import { bytesToString } from "@/utils/utils";
import { getAllHistoriesSizeSummary, type HistorySizeSummary } from "./service";

const topTenHistoriesBySizeData = ref<DataValuePoint[] | null>(null);
const activeVsDeletedTotalSizeData = ref<DataValuePoint[] | null>(null);

onMounted(async () => {
    const historiesSizeSummary = await getAllHistoriesSizeSummary();

    topTenHistoriesBySizeData.value = buildTopTenHistoriesBySizeData(historiesSizeSummary);

    activeVsDeletedTotalSizeData.value = buildActiveVsDeletedTotalSizeData(historiesSizeSummary);
});

function buildTopTenHistoriesBySizeData(historiesSizeSummary: HistorySizeSummary[]): DataValuePoint[] {
    const topTenHistoriesBySize = historiesSizeSummary.sort((a, b) => b.size - a.size).slice(0, 10);
    return topTenHistoriesBySize.map((history, index) => ({
        index,
        label: history.name,
        value: history.size,
    }));
}

function buildActiveVsDeletedTotalSizeData(historiesSizeSummary: HistorySizeSummary[]): DataValuePoint[] {
    const activeHistoriesSize = historiesSizeSummary
        .filter((history) => !history.deleted)
        .reduce((total, history) => total + history.size, 0);
    const deletedHistoriesSize = historiesSizeSummary
        .filter((history) => history.deleted)
        .reduce((total, history) => total + history.size, 0);
    return [
        {
            index: 0,
            label: "Active",
            value: activeHistoriesSize,
        },
        {
            index: 1,
            label: "Deleted",
            value: deletedHistoriesSize,
        },
    ];
}

function bytesLabelFormatter(dataPoint: DataValuePoint): string {
    return `${dataPoint.label}: ${bytesToString(dataPoint.value)}`;
}
</script>
<template>
    <div>
        <b-link to="StorageDashboard">{{ localize("Back to Dashboard") }}</b-link>
        <h2 class="text-center my-3">
            <b>Histories Storage Overview</b>
        </h2>
        <p class="text-center">Here you can find various graphs displaying the storage size taken by your histories.</p>
        <PieChart
            v-if="topTenHistoriesBySizeData"
            title="Top 10 Histories by Size"
            :data="topTenHistoriesBySizeData"
            :label-formatter="bytesLabelFormatter"
            :tooltip-formatter="bytesLabelFormatter" />
        <PieChart
            v-if="activeVsDeletedTotalSizeData"
            title="Active vs Deleted Total Size"
            :data="activeVsDeletedTotalSizeData"
            :label-formatter="bytesLabelFormatter"
            :tooltip-formatter="bytesLabelFormatter" />
    </div>
</template>

<style lang="css" scoped>
.pieChart {
    text-align: center;
}
</style>
