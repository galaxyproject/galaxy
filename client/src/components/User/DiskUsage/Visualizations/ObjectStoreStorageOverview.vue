<script setup lang="ts">
import { useRouter } from "vue-router/composables";

import { useObjectStoreStore } from "@/stores/objectStoreStore";
import localize from "@/utils/localization";

import { fetchObjectStoreContentsSizeSummary } from "./service";
import { buildTopNDatasetsBySizeData, byteFormattingForChart, useDataLoading, useDatasetsToDisplay } from "./util";

import BarChart from "./Charts/BarChart.vue";
import OverviewPage from "./OverviewPage.vue";
import SelectedItemActions from "./SelectedItemActions.vue";
import WarnDeletedDatasets from "./WarnDeletedDatasets.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    objectStoreId: string;
}

const props = defineProps<Props>();

const router = useRouter();

const { getObjectStoreNameById } = useObjectStoreStore();

const {
    datasetsSizeSummaryMap,
    topNDatasetsBySizeData,
    isRecoverableDataPoint,
    onUndeleteDataset,
    onPermanentlyDeleteDataset,
} = useDatasetsToDisplay();

const { isLoading, loadDataOnMount } = useDataLoading();

loadDataOnMount(async () => {
    const allDatasetsInObjectStoreSizeSummary = await fetchObjectStoreContentsSizeSummary(props.objectStoreId, 50);
    allDatasetsInObjectStoreSizeSummary.forEach((dataset) => datasetsSizeSummaryMap.set(dataset.id, dataset));

    buildGraphsData();
});

function buildGraphsData() {
    const allDatasetsInObjectStoreSizeSummary = Array.from(datasetsSizeSummaryMap.values());
    topNDatasetsBySizeData.value = buildTopNDatasetsBySizeData(allDatasetsInObjectStoreSizeSummary, 50);
}

async function onViewDataset(datasetId: string) {
    router.push({
        name: "DatasetDetails",
        params: {
            datasetId: datasetId,
        },
    });
}

function onPermDelete(datasetId: string) {
    onPermanentlyDeleteDataset(buildGraphsData, datasetId);
}

function onUndelete(datasetId: string) {
    onUndeleteDataset(buildGraphsData, datasetId);
}
</script>

<template>
    <OverviewPage title="Storage overview by location">
        <p class="text-justify">
            Here you will find some Graphs displaying the storage taken by datasets in the storage location:
            <b>{{ getObjectStoreNameById(objectStoreId) }}</b
            >. You can use these graphs to identify the datasets that take the most space in this storage location.
        </p>
        <WarnDeletedDatasets />
        <div v-if="isLoading" class="text-center">
            <LoadingSpan class="mt-5" :message="localize('Loading your storage data. This may take a while...')" />
        </div>
        <div v-else>
            <BarChart
                v-if="topNDatasetsBySizeData"
                :description="
                    localize(
                        'These are the 50 datasets that take the most space in this storage location. Click on a bar to see more information about the dataset.',
                    )
                "
                v-bind="byteFormattingForChart"
                :enable-selection="true"
                :data="topNDatasetsBySizeData">
                <template v-slot:title>
                    <b>{{ localize("Top 50 Datasets by Size") }}</b>
                </template>
                <template v-slot:selection="{ data }">
                    <SelectedItemActions
                        :data="data"
                        item-type="dataset"
                        :is-recoverable="isRecoverableDataPoint(data)"
                        :can-edit="!isRecoverableDataPoint(data)"
                        @view-item="onViewDataset"
                        @permanently-delete-item="onPermDelete"
                        @undelete-item="onUndelete" />
                </template>
            </BarChart>
        </div>
    </OverviewPage>
</template>
