<script setup lang="ts">
import localize from "@/utils/localization";
import type { DataValuePoint } from "./Charts";
import { ref, onMounted } from "vue";
import PieChart from "./Charts/PieChart.vue";
import { bytesLabelFormatter } from "./Charts/utils";
import { getAllHistoriesSizeSummary, type ItemSizeSummary } from "./service";
import RecoverableItemSizeTooltip from "./RecoverableItemSizeTooltip.vue";
import SelectedHistoryActions from "./SelectedHistoryActions.vue";

const historiesSizeSummaryMap = new Map<string, ItemSizeSummary>();

const topTenHistoriesBySizeData = ref<DataValuePoint[] | null>(null);
const activeVsDeletedTotalSizeData = ref<DataValuePoint[] | null>(null);

onMounted(async () => {
    const allHistoriesSizeSummary = await getAllHistoriesSizeSummary();
    allHistoriesSizeSummary.forEach((history) => historiesSizeSummaryMap.set(history.id, history));

    topTenHistoriesBySizeData.value = buildTopTenHistoriesBySizeData(allHistoriesSizeSummary);
    activeVsDeletedTotalSizeData.value = buildActiveVsDeletedTotalSizeData(allHistoriesSizeSummary);
});

function buildTopTenHistoriesBySizeData(historiesSizeSummary: ItemSizeSummary[]): DataValuePoint[] {
    const topTenHistoriesBySize = historiesSizeSummary.sort((a, b) => b.size - a.size).slice(0, 10);
    return topTenHistoriesBySize.map((history, index) => ({
        index,
        id: history.id,
        label: history.name,
        value: history.size,
    }));
}

function buildActiveVsDeletedTotalSizeData(historiesSizeSummary: ItemSizeSummary[]): DataValuePoint[] {
    const activeHistoriesSize = historiesSizeSummary
        .filter((history) => !history.deleted)
        .reduce((total, history) => total + history.size, 0);
    const deletedHistoriesSize = historiesSizeSummary
        .filter((history) => history.deleted)
        .reduce((total, history) => total + history.size, 0);
    return [
        {
            index: 0,
            id: "active",
            label: "Active",
            value: activeHistoriesSize,
        },
        {
            index: 1,
            id: "deleted",
            label: "Deleted",
            value: deletedHistoriesSize,
        },
    ];
}

function isRecoverableDataPoint(dataPoint?: DataValuePoint): boolean {
    if (dataPoint) {
        const historiesSizeSummary = historiesSizeSummaryMap.get(dataPoint.id || "");
        return historiesSizeSummary?.deleted || dataPoint.id === "deleted";
    }
    return false;
}
</script>
<template>
    <div>
        <router-link :to="{ name: 'StorageDashboard' }">{{ localize("Back to Dashboard") }}</router-link>
        <h2 class="text-center my-3">
            <b>Histories Storage Overview</b>
        </h2>
        <p class="text-center mx-3">
            Here you can find various graphs displaying the storage size taken by <b>all your histories</b>.
        </p>
        <p class="text-center mx-3">
            These graphs include <b>deleted histories</b>. Even if you delete histories, they still take up storage
            space until you permanently delete them. However, you can recover the storage space by permanently deleting
            them from the <i>Discarded Items</i> section of the
            <router-link :to="{ name: 'StorageManager' }"><b>Storage Manager</b></router-link> page.
        </p>
        <PieChart
            v-if="topTenHistoriesBySizeData"
            title="Top 10 Histories by Size"
            description="These are the 10 histories that take the most space on your storage."
            :data="topTenHistoriesBySizeData"
            :enable-selection="true"
            :label-formatter="bytesLabelFormatter">
            <template v-slot:tooltip="{ data }">
                <RecoverableItemSizeTooltip :data="data" :is-recoverable="isRecoverableDataPoint(data)" />
            </template>
            <template v-slot:selection="{ data }">
                <SelectedHistoryActions :data="data" :is-recoverable="isRecoverableDataPoint(data)" />
            </template>
        </PieChart>
        <PieChart
            v-if="activeVsDeletedTotalSizeData"
            title="Active vs Deleted Total Size"
            description="This graph shows the total size of your histories, separated by whether they are active or deleted."
            :data="activeVsDeletedTotalSizeData"
            :label-formatter="bytesLabelFormatter">
            <template v-slot:tooltip="{ data }">
                <RecoverableItemSizeTooltip :data="data" :is-recoverable="isRecoverableDataPoint(data)" />
            </template>
        </PieChart>
    </div>
</template>
