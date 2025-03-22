<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BForm, BFormGroup, BFormSelect, BInputGroup } from "bootstrap-vue";
import { computed, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { useSelectableObjectStores } from "@/composables/useObjectStores";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";

import type { DataValuePoint } from "./Charts";
import { fetchHistoryContentsSizeSummary, type ItemSizeSummary } from "./service";
import {
    buildTopNDatasetsBySizeData,
    byteFormattingForChart,
    useAdvancedFiltering,
    useDataLoading,
    useDatasetsToDisplay,
} from "./util";

import BarChart from "./Charts/BarChart.vue";
import OverviewPage from "./OverviewPage.vue";
import RecoverableItemSizeTooltip from "./RecoverableItemSizeTooltip.vue";
import SelectedItemActions from "./SelectedItemActions.vue";
import WarnDeletedDatasets from "./WarnDeletedDatasets.vue";
import FilterObjectStoreLink from "@/components/Common/FilterObjectStoreLink.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const router = useRouter();
const { getHistoryNameById, getHistoryById } = useHistoryStore();

interface Props {
    historyId: string;
}

const props = defineProps<Props>();

const activeVsDeletedTotalSizeData = ref<DataValuePoint[] | null>(null);
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
const { isAdvanced, toggleAdvanced, inputGroupClasses, faAngleDoubleDown, faAngleDoubleUp } = useAdvancedFiltering();
const { selectableObjectStores, hasSelectableObjectStores } = useSelectableObjectStores();

const objectStore = ref<string>();

const canEditHistory = computed(() => {
    const history = getHistoryById(props.historyId);
    return (history && !history.purged && !history.archived) ?? false;
});

function onChangeObjectStore(value?: string) {
    objectStore.value = value;
    reloadDataFromServer();
}

async function reloadDataFromServer() {
    const allDatasetsInHistorySizeSummary = await fetchHistoryContentsSizeSummary(
        props.historyId,
        numberOfDatasetsLimit,
        objectStore.value
    );
    datasetsSizeSummaryMap.clear();
    allDatasetsInHistorySizeSummary.forEach((dataset) => datasetsSizeSummaryMap.set(dataset.id, dataset));

    buildGraphsData();
}

loadDataOnMount(reloadDataFromServer);

function buildGraphsData() {
    const allDatasetsInHistorySizeSummary = Array.from(datasetsSizeSummaryMap.values());
    topNDatasetsBySizeData.value = buildTopNDatasetsBySizeData(
        allDatasetsInHistorySizeSummary,
        numberOfDatasetsToDisplay.value
    );
    activeVsDeletedTotalSizeData.value = buildActiveVsDeletedTotalSizeData(allDatasetsInHistorySizeSummary);
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
            label: "活跃",
            value: activeDatasetsSize,
        },
        {
            id: "deleted",
            label: "已删除",
            value: deletedDatasetsSize,
        },
    ];
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

function onPermDelete(datasetId: string) {
    onPermanentlyDeleteDataset(buildGraphsData, datasetId);
}

function onUndelete(datasetId: string) {
    onUndeleteDataset(buildGraphsData, datasetId);
}
</script>
<template>
    <OverviewPage class="history-storage-overview" title="历史存储概览">
        <p class="text-justify">
            在这里您将看到一些展示历史中数据集存储空间的图表:
            <b>{{ getHistoryNameById(props.historyId) }}</b
            >。您可以使用这些图表来识别在您历史中占用最多空间的数据集。您也可以
            前往
            <router-link :to="{ name: 'HistoriesOverview' }"><b>历史存储概览</b></router-link> 页面查看
            <b>所有历史</b>占用的存储空间。
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
                        `这是该历史中占用空间最多的 ${numberOfDatasetsToDisplay} 个数据集。点击柱状图可查看关于该数据集的更多信息。`
                    )
                "
                :data="topNDatasetsBySizeData"
                :enable-selection="true"
                v-bind="byteFormattingForChart">
                <template v-slot:title>
                    <b>{{ localize(`按大小排名前 ${numberOfDatasetsToDisplay} 的数据集`) }}</b>
                    <BInputGroup size="sm" :class="inputGroupClasses">
                        <BFormSelect
                            v-if="!isAdvanced"
                            v-model="numberOfDatasetsToDisplay"
                            :options="numberOfDatasetsToDisplayOptions"
                            :disabled="isLoading"
                            title="显示的历史数量"
                            size="sm"
                            @change="buildGraphsData()">
                        </BFormSelect>
                        <BButton
                            v-b-tooltip.hover.bottom.noninteractive
                            aria-haspopup="true"
                            size="sm"
                            title="切换高级过滤"
                            data-description="宽切换高级过滤"
                            @click="toggleAdvanced">
                            <FontAwesomeIcon :icon="isAdvanced ? faAngleDoubleUp : faAngleDoubleDown" />
                        </BButton>
                    </BInputGroup>
                </template>
                <template v-slot:options>
                    <div v-if="isAdvanced" class="clear-fix">
                        <BForm>
                            <BFormGroup
                                id="input-group-num-histories"
                                label="历史数量："
                                label-for="input-num-histories"
                                description="这是将显示的最大历史数量。">
                                <BFormSelect
                                    v-model="numberOfDatasetsToDisplay"
                                    :options="numberOfDatasetsToDisplayOptions"
                                    :disabled="isLoading"
                                    title="显示的历史数量"
                                    @change="buildGraphsData()">
                                </BFormSelect>
                            </BFormGroup>
                            <BFormGroup
                                v-if="selectableObjectStores && hasSelectableObjectStores"
                                id="input-group-object-store"
                                label="存储位置："
                                label-for="input-object-store"
                                description="这将限制历史大小计算到特定存储位置。">
                                <FilterObjectStoreLink
                                    :object-stores="selectableObjectStores"
                                    :value="objectStore"
                                    @change="onChangeObjectStore" />
                            </BFormGroup>
                        </BForm>
                    </div>
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
                        :can-edit="canEditHistory"
                        @view-item="onViewDataset"
                        @undelete-item="onUndelete"
                        @permanently-delete-item="onPermDelete" />
                </template>
            </BarChart>

            <BarChart
                v-if="activeVsDeletedTotalSizeData"
                :title="localize('活跃与已删除总大小')"
                :description="
                    localize(
                        '此图表显示了您在此历史中数据集的总大小，分为活跃和已删除的数据集。'
                    )
                "
                :data="activeVsDeletedTotalSizeData"
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
