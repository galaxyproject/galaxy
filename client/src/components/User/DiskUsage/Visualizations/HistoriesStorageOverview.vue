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
    const allHistoriesSizeSummary = await getAllHistoriesSizeSummary();

    topTenHistoriesBySizeData.value = buildTopTenHistoriesBySizeData(allHistoriesSizeSummary);
    activeVsDeletedTotalSizeData.value = buildActiveVsDeletedTotalSizeData(allHistoriesSizeSummary);
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
        <p class="text-center mx-5">
            Here you can find various graphs displaying the storage size taken by all your histories. This includes
            deleted histories, as they still take storage space until their contents are permanently deleted. You can
            always recover the space by permanently deleting those from the <i>Discarded Items</i> section of the
            <b-link to="management">
                <b>Storage Manager</b>
            </b-link>
            page.
        </p>
        <PieChart
            v-if="topTenHistoriesBySizeData"
            title="Top 10 Histories by Size"
            description="These are the 10 histories that take the most space on your storage."
            :data="topTenHistoriesBySizeData"
            :label-formatter="bytesLabelFormatter"
            :tooltip-formatter="bytesLabelFormatter" />
        <PieChart
            v-if="activeVsDeletedTotalSizeData"
            title="Active vs Deleted Total Size"
            description="This graph shows the total size of your histories, separated by whether they are active or deleted."
            :data="activeVsDeletedTotalSizeData"
            :label-formatter="bytesLabelFormatter"
            :tooltip-formatter="bytesLabelFormatter" />
    </div>
</template>
