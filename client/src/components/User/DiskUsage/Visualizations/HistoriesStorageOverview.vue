<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router/composables";

import { useConfirmDialog } from "@/composables/confirmDialog";
import { useToast } from "@/composables/toast";
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
            label: "Active",
            value: activeHistoriesSize,
        },
        {
            id: "archived",
            label: "Archived",
            value: archivedHistoriesSize,
        },
        {
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

function isArchivedDataPoint(dataPoint: DataValuePoint): boolean {
    if (dataPoint) {
        const historiesSizeSummary = historiesSizeSummaryMap.get(dataPoint.id);
        return historiesSizeSummary?.archived || false;
    }
    return false;
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
            successToast(localize("History undeleted successfully."));
            buildGraphsData();
        }
    } catch (error) {
        errorToast(`${error}`, localize("An error occurred while undeleting the history."));
    }
}

async function onPermanentlyDeleteHistory(historyId: string) {
    const confirmed = await confirm(
        localize("Are you sure you want to permanently delete this history? This action cannot be undone."),
        {
            title: localize("Permanently delete history?"),
            okVariant: "danger",
            okTitle: localize("Permanently delete"),
            cancelTitle: localize("Cancel"),
            cancelVariant: "outline-primary",
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
            successToast(localize("History permanently deleted successfully."));
            buildGraphsData();
        }
    } catch (error) {
        errorToast(`${error}`, localize("An error occurred while permanently deleting the history."));
    }
}
</script>
<template>
    <OverviewPage title="Histories Storage Overview">
        <p class="text-justify">
            Here you can find various graphs displaying the storage size taken by <b>all your histories</b>.
        </p>
        <WarnDeletedHistories />

        <div v-if="isLoading" class="text-center">
            <LoadingSpan class="mt-5" :message="localize('Loading your storage data. This may take a while...')" />
        </div>
        <div v-else>
            <BarChart
                v-if="topTenHistoriesBySizeData"
                :description="
                    localize(
                        `These are the ${numberOfHistoriesToDisplay} histories that take the most space on your storage. Click on a bar to see more information about the history.`
                    )
                "
                :data="topTenHistoriesBySizeData"
                :enable-selection="true"
                v-bind="byteFormattingForChart">
                <template v-slot:title>
                    <b>{{ localize(`Top ${numberOfHistoriesToDisplay} Histories by Size`) }}</b>
                    <b-form-select
                        v-model="numberOfHistoriesToDisplay"
                        :options="numberOfHistoriesToDisplayOptions"
                        :disabled="isLoading"
                        title="Number of histories to show"
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
                        @view-item="onViewHistory"
                        @undelete-item="onUndeleteHistory"
                        @permanently-delete-item="onPermanentlyDeleteHistory" />
                </template>
            </BarChart>
            <BarChart
                v-if="activeVsArchivedVsDeletedTotalSizeData"
                :title="localize('Active vs Archived vs Deleted Total Size')"
                :description="
                    localize(
                        'This graph shows the total size taken by your histories, split between active, archived and deleted histories.'
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
