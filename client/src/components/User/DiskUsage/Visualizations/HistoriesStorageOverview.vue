<script setup lang="ts">
import { BLink } from "bootstrap-vue";
import localize from "@/utils/localization";
import type { DataValuePoint } from "./Charts";
import { ref, computed, onMounted } from "vue";
import PieChart from "./Charts/PieChart.vue";
import { bytesToString } from "@/utils/utils";
import { getAllHistoriesSizeSummary, type ItemSizeSummary } from "./service";

const historiesSizeSummaryMap = new Map<string, ItemSizeSummary>();

const topTenHistoriesBySizeData = ref<DataValuePoint[] | null>(null);
const activeVsDeletedTotalSizeData = ref<DataValuePoint[] | null>(null);

const chartTooltip = ref<HTMLBaseElement | null>(null);
const currentlyHoveredDataPoint = ref<DataValuePoint | null>(null);
const currentlyHoveredDataPointIsRecoverable = computed(() => {
    if (currentlyHoveredDataPoint.value) {
        const historiesSizeSummary = historiesSizeSummaryMap.get(currentlyHoveredDataPoint.value?.id || "");
        return historiesSizeSummary?.deleted || currentlyHoveredDataPoint.value.id === "deleted";
    }
    return false;
});

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

function bytesLabelFormatter(dataPoint: DataValuePoint): string {
    return `${dataPoint.label}: ${bytesToString(dataPoint.value)}`;
}

function onShowTooltip(dataPoint: DataValuePoint, mouseX: number, mouseY: number): void {
    currentlyHoveredDataPoint.value = dataPoint;
    setTooltipPosition(mouseX, mouseY);
}
function onMoveTooltip(mouseX: number, mouseY: number): void {
    setTooltipPosition(mouseX, mouseY);
}

function onHideTooltip(): void {
    currentlyHoveredDataPoint.value = null;
}

function setTooltipPosition(mouseX: number, mouseY: number): void {
    if (chartTooltip.value) {
        chartTooltip.value.style.left = `${mouseX}px`;
        chartTooltip.value.style.top = `${mouseY}px`;
    }
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
            :tooltip-formatter="bytesLabelFormatter"
            @show-tooltip="onShowTooltip"
            @move-tooltip="onMoveTooltip"
            @hide-tooltip="onHideTooltip" />
        <PieChart
            v-if="activeVsDeletedTotalSizeData"
            title="Active vs Deleted Total Size"
            description="This graph shows the total size of your histories, separated by whether they are active or deleted."
            :data="activeVsDeletedTotalSizeData"
            :label-formatter="bytesLabelFormatter"
            :tooltip-formatter="bytesLabelFormatter"
            @show-tooltip="onShowTooltip"
            @move-tooltip="onMoveTooltip"
            @hide-tooltip="onHideTooltip" />

        <div v-show="currentlyHoveredDataPoint" ref="chartTooltip" class="chartTooltip">
            <div class="h-md mx-2">{{ currentlyHoveredDataPoint?.label ?? "No data" }}</div>
            <b class="h-md m-2">{{ bytesToString(currentlyHoveredDataPoint?.value ?? 0) }}</b>
            <div v-if="currentlyHoveredDataPointIsRecoverable" class="text-muted mx-2">Recoverable storage space</div>
        </div>
    </div>
</template>

<style scoped>
.chartTooltip {
    position: absolute;
    background-color: #fff;
    border: 1px solid #000;
    border-radius: 5px;
    padding: 5px;
    box-shadow: 0 0 5px 0 rgba(0, 0, 0, 0.5);
    margin: 0 0 0 20px;
    z-index: 100;
    text-align: center;
}
</style>
