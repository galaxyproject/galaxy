<script setup lang="ts">
import localize from "@/utils/localization";
import type { DataValuePoint } from "./Charts";
import { ref, onMounted } from "vue";
import PieChart from "./Charts/PieChart.vue";
import { bytesLabelFormatter } from "./Charts/utils";
import { getAllHistoriesSizeSummary, type ItemSizeSummary, undeleteHistory, purgeHistory } from "./service";
import RecoverableItemSizeTooltip from "./RecoverableItemSizeTooltip.vue";
import SelectedItemActions from "./SelectedItemActions.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import { useRouter } from "vue-router/composables";
import { useToast } from "@/composables/toast";
import { useConfirmDialog } from "@/composables/confirmDialog";

const router = useRouter();
const { success: successToast, error: errorToast } = useToast();
const { confirm } = useConfirmDialog();

const historiesSizeSummaryMap = new Map<string, ItemSizeSummary>();
const topTenHistoriesBySizeData = ref<DataValuePoint[] | null>(null);
const activeVsDeletedTotalSizeData = ref<DataValuePoint[] | null>(null);
const isLoading = ref(true);

onMounted(async () => {
    isLoading.value = true;
    const allHistoriesSizeSummary = await getAllHistoriesSizeSummary();
    allHistoriesSizeSummary.forEach((history) => historiesSizeSummaryMap.set(history.id, history));

    buildGraphsData(allHistoriesSizeSummary);
    isLoading.value = false;
});

function buildGraphsData(allHistoriesSizeSummary: ItemSizeSummary[]) {
    topTenHistoriesBySizeData.value = buildTopTenHistoriesBySizeData(allHistoriesSizeSummary);
    activeVsDeletedTotalSizeData.value = buildActiveVsDeletedTotalSizeData(allHistoriesSizeSummary);
}

function buildTopTenHistoriesBySizeData(historiesSizeSummary: ItemSizeSummary[]): DataValuePoint[] {
    const topTenHistoriesBySize = historiesSizeSummary.sort((a, b) => b.size - a.size).slice(0, 10);
    return topTenHistoriesBySize.map((history) => ({
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
            id: "active",
            label: "Active",
            value: activeHistoriesSize,
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

function onViewHistory(historyId: string) {
    router.push({ name: "HistoryOverview", params: { historyId } });
}

async function onUndeleteHistory(historyId: string) {
    try {
        const result = await undeleteHistory(historyId);
        const history = historiesSizeSummaryMap.get(historyId);
        if (history && !result.deleted) {
            history.deleted = result.deleted;
            historiesSizeSummaryMap.set(historyId, history);
            successToast(localize("History undeleted successfully."));
            buildGraphsData(Array.from(historiesSizeSummaryMap.values()));
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
        const result = await purgeHistory(historyId);
        const history = historiesSizeSummaryMap.get(historyId);
        if (history && result.purged) {
            historiesSizeSummaryMap.delete(historyId);
            successToast(localize("History permanently deleted successfully."));
            buildGraphsData(Array.from(historiesSizeSummaryMap.values()));
        }
    } catch (error) {
        errorToast(`${error}`, localize("An error occurred while permanently deleting the history."));
    }
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
                    <SelectedItemActions
                        :data="data"
                        :item-type="localize('history')"
                        :is-recoverable="isRecoverableDataPoint(data)"
                        @view-item="onViewHistory"
                        @undelete-item="onUndeleteHistory"
                        @permanently-delete-item="onPermanentlyDeleteHistory" />
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
    </div>
</template>
