<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router/composables";

import { useConfirmDialog } from "@/composables/confirmDialog";
import { useToast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";

import type { DataValuePoint } from "./Charts";
import { fetchAllHistoriesSizeSummary, type ItemSizeSummary, purgeHistoryById, undeleteHistoryById } from "./service";
import { byteFormattingForChart, useDataLoading } from "./util";

import BarChart from "./Charts/BarChart.vue";
import OverviewPage from "./OverviewPage.vue";
import RecoverableItemSizeTooltip from "./RecoverableItemSizeTooltip.vue";
import SelectedItemActions from "./SelectedItemActions.vue";
import WarnDeletedHistories from "./WarnDeletedHistories.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const historyStore = useHistoryStore();
const router = useRouter();
const { success: successToast, error: errorToast } = useToast();
const { confirm } = useConfirmDialog();

const historiesSizeSummaryMap = new Map<string, ItemSizeSummary>();
const topTenHistoriesBySizeData = ref<DataValuePoint[] | null>(null);
const activeVsArchivedVsDeletedTotalSizeData = ref<DataValuePoint[] | null>(null);
const numberOfHistoriesToDisplayOptions = [10, 20, 50];
const numberOfHistoriesToDisplay = ref(numberOfHistoriesToDisplayOptions[0]);

const { isLoading, loadDataOnMount } = useDataLoading();

loadDataOnMount(async () => {
    const allHistoriesSizeSummary = await fetchAllHistoriesSizeSummary();
    allHistoriesSizeSummary.forEach((history) => historiesSizeSummaryMap.set(history.id, history));

    buildGraphsData();
});

function buildGraphsData() {
    const allHistoriesSizeSummary = Array.from(historiesSizeSummaryMap.values());
    topTenHistoriesBySizeData.value = buildTopHistoriesBySizeData(allHistoriesSizeSummary);
    activeVsArchivedVsDeletedTotalSizeData.value = buildActiveVsArchivedVsDeletedTotalSizeData(allHistoriesSizeSummary);
}

function buildTopHistoriesBySizeData(historiesSizeSummary: ItemSizeSummary[]): DataValuePoint[] {
    const topTenHistoriesBySize = historiesSizeSummary
        .sort((a, b) => b.size - a.size)
        .slice(0, numberOfHistoriesToDisplay.value);
    return topTenHistoriesBySize.map((history) => ({
        id: history.id,
        label: history.name,
        value: history.size,
    }));
}

function buildActiveVsArchivedVsDeletedTotalSizeData(historiesSizeSummary: ItemSizeSummary[]): DataValuePoint[] {
    const activeHistoriesSize = historiesSizeSummary
        .filter((history) => !history.deleted && !history.archived)
        .reduce((total, history) => total + history.size, 0);
    const archivedHistoriesSize = historiesSizeSummary
        .filter((history) => history.archived)
        .reduce((total, history) => total + history.size, 0);
    const deletedHistoriesSize = historiesSizeSummary
        .filter((history) => history.deleted)
        .reduce((total, history) => total + history.size, 0);
    return [
        {
            id: "active",
            label: "活跃",
            value: activeHistoriesSize,
        },
        {
            id: "archived",
            label: "已归档",
            value: archivedHistoriesSize,
        },
        {
            id: "deleted",
            label: "已删除",
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

function isArchivedDataPoint(dataPoint: DataValuePoint): boolean {
    if (dataPoint) {
        const historiesSizeSummary = historiesSizeSummaryMap.get(dataPoint.id);
        return historiesSizeSummary?.archived || false;
    }
    return false;
}

async function onSetCurrentHistory(historyId: string) {
    await historyStore.setCurrentHistory(historyId);
    router.push({ path: "/" });
}

function onViewHistory(historyId: string) {
    router.push({ name: "HistoryOverview", params: { historyId } });
}

async function onUndeleteHistory(historyId: string) {
    try {
        const result = await undeleteHistoryById(historyId);
        const history = historiesSizeSummaryMap.get(historyId);
        if (history && !result.deleted) {
            history.deleted = result.deleted;
            historiesSizeSummaryMap.set(historyId, history);
            successToast(localize("历史记录已成功恢复。"));
            buildGraphsData();
        }
    } catch (error) {
        errorToast(`${error}`, localize("恢复历史记录时发生错误。"));
    }
}

async function onPermanentlyDeleteHistory(historyId: string) {
    const confirmed = await confirm(
        localize("您确定要永久删除此历史记录吗？此操作无法撤消。"),
        {
            title: localize("永久删除历史记录？"),
            okVariant: "danger",
            okTitle: localize("永久删除"),
            cancelTitle: localize("取消"),
        }
    );
    if (!confirmed) {
        return;
    }
    try {
        const result = await purgeHistoryById(historyId);
        const history = historiesSizeSummaryMap.get(historyId);
        if (history && result.purged) {
            historiesSizeSummaryMap.delete(historyId);
            successToast(localize("历史记录已成功永久删除。"));
            buildGraphsData();
        }
    } catch (error) {
        errorToast(`${error}`, localize("永久删除历史记录时发生错误。"));
    }
}
</script>
<template>
    <OverviewPage title="历史记录存储概览">
        <p class="text-justify">
            在此您可以查看显示<b>所有历史记录</b>占用存储空间大小的各种图表。
        </p>
        <WarnDeletedHistories />

        <div v-if="isLoading" class="text-center">
            <LoadingSpan class="mt-5" :message="localize('正在加载您的存储数据。这可能需要一些时间...')" />
        </div>
        <div v-else>
            <BarChart
                v-if="topTenHistoriesBySizeData"
                :description="
                    localize(
                        `这是占用存储空间最多的 ${numberOfHistoriesToDisplay} 条历史记录。点击柱状图可查看有关历史记录的更多信息。`
                    )
                "
                :data="topTenHistoriesBySizeData"
                :enable-selection="true"
                v-bind="byteFormattingForChart">
                <template v-slot:title>
                    <b>{{ localize(`按大小排序的前 ${numberOfHistoriesToDisplay} 条历史记录`) }}</b>
                    <b-form-select
                        v-model="numberOfHistoriesToDisplay"
                        :options="numberOfHistoriesToDisplayOptions"
                        :disabled="isLoading"
                        title="显示历史记录的数量"
                        class="float-right w-auto"
                        size="sm"
                        @change="buildGraphsData()">
                    </b-form-select>
                </template>
                <template v-slot:tooltip="{ data }">
                    <RecoverableItemSizeTooltip
                        v-if="data"
                        :data="data"
                        :is-recoverable="isRecoverableDataPoint(data)"
                        :is-archived="isArchivedDataPoint(data)" />
                </template>
                <template v-slot:selection="{ data }">
                    <SelectedItemActions
                        :data="data"
                        item-type="history"
                        :is-recoverable="isRecoverableDataPoint(data)"
                        :is-archived="isArchivedDataPoint(data)"
                        :can-edit="!isArchivedDataPoint(data)"
                        @set-current-history="onSetCurrentHistory"
                        @view-item="onViewHistory"
                        @undelete-item="onUndeleteHistory"
                        @permanently-delete-item="onPermanentlyDeleteHistory" />
                </template>
            </BarChart>
            <BarChart
                v-if="activeVsArchivedVsDeletedTotalSizeData"
                :title="localize('活跃与已归档与已删除的总大小对比')"
                :description="
                    localize(
                        '此图表显示了您的历史记录占用的总大小，按活跃、已归档和已删除的历史记录进行分类。'
                    )
                "
                :data="activeVsArchivedVsDeletedTotalSizeData"
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
