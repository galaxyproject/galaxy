<script setup lang="ts">
import { useRouter } from "vue-router/composables";

import { useObjectStoreStore } from "@/stores/objectStoreStore";
import localize from "@/utils/localization";

import { fetchObjectStoreContentsSizeSummary } from "./service";
import { buildTopNDatasetsBySizeData, byteFormattingForChart, useDataLoading, useDatasetsToDisplay } from "./util";

import BarChart from "./Charts/BarChart.vue";
import OverviewPage from "./OverviewPage.vue";
import RecoverableItemSizeTooltip from "./RecoverableItemSizeTooltip.vue";
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
    numberOfDatasetsToDisplayOptions,
    numberOfDatasetsToDisplay,
    numberOfDatasetsLimit,
    datasetsSizeSummaryMap,
    topNDatasetsBySizeData,
    isRecoverableDataPoint,
    onUndeleteDataset,
    onPermanentlyDeleteDataset,
} = useDatasetsToDisplay();

const { isLoading, loadDataOnMount } = useDataLoading();

loadDataOnMount(async () => {
    const allDatasetsInObjectStoreSizeSummary = await fetchObjectStoreContentsSizeSummary(
        props.objectStoreId,
        numberOfDatasetsLimit
    );
    allDatasetsInObjectStoreSizeSummary.forEach((dataset) => datasetsSizeSummaryMap.set(dataset.id, dataset));

    buildGraphsData();
});

function buildGraphsData() {
    const allDatasetsInObjectStoreSizeSummary = Array.from(datasetsSizeSummaryMap.values());
    topNDatasetsBySizeData.value = buildTopNDatasetsBySizeData(
        allDatasetsInObjectStoreSizeSummary,
        numberOfDatasetsToDisplay.value
    );
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
    <OverviewPage title="按位置显示存储概览">
        <p class="text-justify">
            这里您将看到一些图表，显示存储位置中数据集所占用的存储空间：
            <b>{{ getObjectStoreNameById(objectStoreId) }}</b
            >。您可以使用这些图表来识别在此存储位置中占用最多空间的数据集。
        </p>
        <WarnDeletedDatasets />
        <div v-if="isLoading" class="text-center">
            <LoadingSpan class="mt-5" :message="localize('正在加载您的存储数据。这可能需要一些时间...')" />
        </div>
        <div v-else>
            <BarChart
                v-if="topNDatasetsBySizeData"
                :description="
                    localize(
                        `这些是在此历史记录中占用最多空间的${numberOfDatasetsToDisplay}个数据集。点击条形图可查看有关数据集的更多信息。`
                    )
                "
                v-bind="byteFormattingForChart"
                :enable-selection="true"
                :data="topNDatasetsBySizeData">
                <template v-slot:title>
                    <b>{{ localize(`按大小排列的前${numberOfDatasetsToDisplay}个数据集`) }}</b>
                    <b-form-select
                        v-model="numberOfDatasetsToDisplay"
                        :options="numberOfDatasetsToDisplayOptions"
                        :disabled="isLoading"
                        title="显示的数据集数量"
                        class="float-right w-auto"
                        size="sm"
                        @change="buildGraphsData()">
                    </b-form-select>
                </template>
                <template v-slot:tooltip="{ data }">
                    <RecoverableItemSizeTooltip
                        v-if="data"
                        :data="data"
                        :is-recoverable="isRecoverableDataPoint(data)" />
                </template>
                <template v-slot:selection="{ data }">
                    <SelectedItemActions
                        :data="data"
                        item-type="dataset"
                        :is-recoverable="isRecoverableDataPoint(data)"
                        @view-item="onViewDataset"
                        @permanently-delete-item="onPermDelete"
                        @undelete-item="onUndelete" />
                </template>
            </BarChart>
        </div>
    </OverviewPage>
</template>
