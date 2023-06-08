<script setup lang="ts">
import localize from "@/utils/localization";
import type { DataValuePoint } from "./Charts";
import { ref, onMounted } from "vue";
import BarChart from "./Charts/BarChart.vue";
import { bytesLabelFormatter, bytesValueFormatter } from "./Charts/formatters";
import {
    fetchHistoryContentsSizeSummary,
    type ItemSizeSummary,
    undeleteDatasetById,
    purgeDatasetById,
} from "./service";
import RecoverableItemSizeTooltip from "./RecoverableItemSizeTooltip.vue";
import SelectedItemActions from "./SelectedItemActions.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import Heading from "@/components/Common/Heading.vue";
import { useRouter } from "vue-router/composables";
import { useToast } from "@/composables/toast";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useHistoryStore } from "@/stores/historyStore";

const router = useRouter();
const { success: successToast, error: errorToast } = useToast();
const { confirm } = useConfirmDialog();
const { getHistoryNameById } = useHistoryStore();

const props = defineProps({
    historyId: {
        type: String,
        required: true,
    },
});

const datasetsSizeSummaryMap = new Map<string, ItemSizeSummary>();
const topTenDatasetsBySizeData = ref<DataValuePoint[] | null>(null);
const activeVsDeletedTotalSizeData = ref<DataValuePoint[] | null>(null);
const isLoading = ref(true);
const numberOfDatasetsToDisplayOptions = [10, 20, 50];
const numberOfDatasetsToDisplay = ref(numberOfDatasetsToDisplayOptions[0]);

onMounted(async () => {
    isLoading.value = true;
    const limit = Math.max(...numberOfDatasetsToDisplayOptions);
    const allDatasetsInHistorySizeSummary = await fetchHistoryContentsSizeSummary(props.historyId, limit);
    allDatasetsInHistorySizeSummary.forEach((dataset) => datasetsSizeSummaryMap.set(dataset.id, dataset));

    buildGraphsData();
    isLoading.value = false;
});

function buildGraphsData() {
    const allDatasetsInHistorySizeSummary = Array.from(datasetsSizeSummaryMap.values());
    topTenDatasetsBySizeData.value = buildTopTenDatasetsBySizeData(allDatasetsInHistorySizeSummary);
    activeVsDeletedTotalSizeData.value = buildActiveVsDeletedTotalSizeData(allDatasetsInHistorySizeSummary);
}

function buildTopTenDatasetsBySizeData(datasetsSizeSummary: ItemSizeSummary[]): DataValuePoint[] {
    const topTenDatasetsBySize = datasetsSizeSummary
        .sort((a, b) => b.size - a.size)
        .slice(0, numberOfDatasetsToDisplay.value);
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

async function onViewDataset(datasetId: string) {
    router.push({
        name: "DatasetDetails",
        params: {
            historyId: props.historyId,
            datasetId: datasetId,
        },
    });
}

async function onUndeleteDataset(datasetId: string) {
    try {
        const result = await undeleteDatasetById(props.historyId, datasetId);
        const dataset = datasetsSizeSummaryMap.get(datasetId);
        if (dataset && !result.deleted) {
            dataset.deleted = result.deleted;
            datasetsSizeSummaryMap.set(datasetId, dataset);
            successToast(localize("Dataset undeleted successfully."));
            buildGraphsData();
        }
    } catch (error) {
        errorToast(`${error}`, localize("An error occurred while undeleting the dataset."));
    }
}

async function onPermanentlyDeleteDataset(datasetId: string) {
    const confirmed = await confirm(
        localize("Are you sure you want to permanently delete this dataset? This action cannot be undone."),
        {
            title: localize("Permanently delete dataset?"),
            okVariant: "danger",
            okTitle: localize("Permanently delete"),
            cancelTitle: localize("Cancel"),
        }
    );
    if (!confirmed) {
        return;
    }
    try {
        const result = await purgeDatasetById(props.historyId, datasetId);
        const dataset = datasetsSizeSummaryMap.get(datasetId);
        if (dataset && result) {
            datasetsSizeSummaryMap.delete(datasetId);
            successToast(localize("Dataset permanently deleted successfully."));
            buildGraphsData();
        }
    } catch (error) {
        errorToast(`${error}`, localize("An error occurred while permanently deleting the dataset."));
    }
}
</script>
<template>
    <div class="mx-3 history-storage-overview">
        <router-link :to="{ name: 'StorageDashboard' }">{{ localize("Back to Dashboard") }}</router-link>
        <Heading h1 bold class="my-3"> History Storage Overview </Heading>
        <p class="text-justify">
            Here you will find some Graphs displaying the storage taken by datasets in your history:
            <b>{{ getHistoryNameById(props.historyId) }}</b
            >. You can use these graphs to identify the datasets that take the most space in your history. You can also
            go to the
            <router-link :to="{ name: 'HistoriesOverview' }"><b>Histories Storage Overview</b></router-link> page to see
            the storage taken by <b>all your histories</b>.
        </p>
        <p class="text-justify">
            Note: these graphs include <b>deleted datasets</b>. Remember that, even if you delete datasets, they still
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
                v-if="topTenDatasetsBySizeData"
                :description="
                    localize(
                        'These are the 10 datasets that take the most space in this history. Click on a bar to see more information about the dataset.'
                    )
                "
                :enable-selection="true"
                :data="topTenDatasetsBySizeData"
                :label-formatter="bytesLabelFormatter"
                :value-formatter="bytesValueFormatter">
                <template v-slot:title>
                    <b>{{ localize(`Top ${numberOfDatasetsToDisplay} Datasets by Size`) }}</b>
                    <b-form-select
                        v-model="numberOfDatasetsToDisplay"
                        :options="numberOfDatasetsToDisplayOptions"
                        :disabled="isLoading"
                        title="Number of histories to show"
                        class="float-right w-auto"
                        size="sm"
                        @change="buildGraphsData()">
                    </b-form-select>
                </template>
                <template v-slot:tooltip="{ data }">
                    <RecoverableItemSizeTooltip :data="data" :is-recoverable="isRecoverableDataPoint(data)" />
                </template>
                <template v-slot:selection="{ data }">
                    <SelectedItemActions
                        :data="data"
                        item-type="dataset"
                        :is-recoverable="isRecoverableDataPoint(data)"
                        @view-item="onViewDataset"
                        @undelete-item="onUndeleteDataset"
                        @permanently-delete-item="onPermanentlyDeleteDataset" />
                </template>
            </BarChart>

            <BarChart
                v-if="activeVsDeletedTotalSizeData"
                :title="localize('Active vs Deleted Total Size')"
                :description="
                    localize(
                        'This graph shows the total size of your datasets in this history, split between active and deleted datasets.'
                    )
                "
                :data="activeVsDeletedTotalSizeData"
                :label-formatter="bytesLabelFormatter"
                :value-formatter="bytesValueFormatter">
                <template v-slot:tooltip="{ data }">
                    <RecoverableItemSizeTooltip :data="data" :is-recoverable="isRecoverableDataPoint(data)" />
                </template>
            </BarChart>
        </div>
    </div>
</template>
