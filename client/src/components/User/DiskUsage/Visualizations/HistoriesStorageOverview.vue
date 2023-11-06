<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { useConfirmDialog } from "@/composables/confirmDialog";
import { useToast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";

import type { DataValuePoint } from "./Charts";
import { bytesLabelFormatter, bytesValueFormatter } from "./Charts/formatters";
import { fetchAllHistoriesSizeSummary, type ItemSizeSummary, purgeHistoryById, undeleteHistoryById } from "./service";

import BarChart from "./Charts/BarChart.vue";
import RecoverableItemSizeTooltip from "./RecoverableItemSizeTooltip.vue";
import SelectedItemActions from "./SelectedItemActions.vue";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const historyStore = useHistoryStore();
const router = useRouter();
const { success: successToast, error: errorToast } = useToast();
const { confirm } = useConfirmDialog();

const historiesSizeSummaryMap = new Map<string, ItemSizeSummary>();
const topTenHistoriesBySizeData = ref<DataValuePoint[] | null>(null);
const activeVsArchivedVsDeletedTotalSizeData = ref<DataValuePoint[] | null>(null);
const isLoading = ref(true);
const numberOfHistoriesToDisplayOptions = [10, 20, 50];
const numberOfHistoriesToDisplay = ref(numberOfHistoriesToDisplayOptions[0]);

onMounted(async () => {
    isLoading.value = true;
    const allHistoriesSizeSummary = await fetchAllHistoriesSizeSummary();
    allHistoriesSizeSummary.forEach((history) => historiesSizeSummaryMap.set(history.id, history));

    buildGraphsData();
    isLoading.value = false;
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
    <div class="mx-3">
        <router-link :to="{ name: 'StorageDashboard' }">{{ localize("Back to Dashboard") }}</router-link>
        <Heading h1 bold class="my-3"> Histories Storage Overview </Heading>
        <p class="text-justify">
            Here you can find various graphs displaying the storage size taken by <b>all your histories</b>.
        </p>
        <p class="text-justify">
            Note: these graphs include <b>deleted histories</b>. Remember that, even if you delete histories, they still
            take up storage space. However, you can free up the storage space by permanently deleting them from the
            <i>Discarded Items</i> section of the
            <router-link :to="{ name: 'StorageManager' }"><b>Storage Manager</b></router-link> page or by selecting them
            individually in the graph and clicking the <b>Permanently Delete</b> button.
        </p>

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
                :label-formatter="bytesLabelFormatter"
                :value-formatter="bytesValueFormatter">
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
                        @set-current-history="onSetCurrentHistory"
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
                :label-formatter="bytesLabelFormatter"
                :value-formatter="bytesValueFormatter">
                <template v-slot:tooltip="{ data }">
                    <RecoverableItemSizeTooltip
                        v-if="data"
                        :data="data"
                        :is-recoverable="isRecoverableDataPoint(data)" />
                </template>
            </BarChart>
        </div>
    </div>
</template>
