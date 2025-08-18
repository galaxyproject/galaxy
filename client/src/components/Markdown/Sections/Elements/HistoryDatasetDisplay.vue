<template>
    <b-card body-class="p-0">
        <b-card-header v-if="!embedded">
            <span class="float-right">
                <b-button
                    v-b-tooltip.hover
                    :href="downloadUrl"
                    variant="link"
                    size="sm"
                    role="button"
                    title="Download Dataset"
                    type="button"
                    class="py-0 px-1">
                    <span class="fa fa-download" />
                </b-button>
                <b-button
                    v-b-tooltip.hover
                    :href="importUrl"
                    role="button"
                    variant="link"
                    title="Import Dataset"
                    type="button"
                    class="py-0 px-1">
                    <span class="fa fa-file-import" />
                </b-button>
                <b-button
                    v-if="expandable && expanded"
                    v-b-tooltip.hover
                    href="#"
                    role="button"
                    variant="link"
                    title="Collapse"
                    type="button"
                    class="py-0 px-1"
                    @click="onExpand">
                    <span class="fa fa-angle-double-up" />
                </b-button>
                <b-button
                    v-else-if="expandable"
                    v-b-tooltip.hover
                    href="#"
                    role="button"
                    variant="link"
                    title="Expand"
                    type="button"
                    class="py-0 px-1"
                    @click="onExpand">
                    <span class="fa fa-angle-double-down" />
                </b-button>
            </span>
            <span>
                <span>Dataset:</span>
                <span class="font-weight-light">{{ metaContent?.name || "..." }}</span>
            </span>
        </b-card-header>
        <b-card-body>
            <div v-if="metaError">{{ metaError }}</div>
            <LoadingSpan v-else-if="!metaType" message="Loading Metadata" />
            <LoadingSpan v-else-if="dataLoading" message="Loading Dataset" />
            <div v-else-if="dataError">{{ dataError }}</div>
            <LoadingSpan v-else-if="datatypesLoading" message="Loading Datatypes" />
            <div v-else-if="!datatypesMapper">Datatypes not loaded.</div>
            <div v-else>
                <b-embed
                    v-if="datatypesMapper.isSubTypeOfAny(metaType, ['pdf', 'html'])"
                    type="iframe"
                    aspect="16by9"
                    :src="displayUrl" />
                <HistoryDatasetAsImage
                    v-else-if="datatypesMapper.isSubTypeOfAny(metaType, ['galaxy.datatypes.images.Image'])"
                    :dataset-id="datasetId" />
                <div v-else-if="dataContent?.item_data">
                    <div v-if="datatypesMapper.isSubTypeOfAny(metaType, ['tabular'])">
                        <b-table
                            id="tabular-dataset-table"
                            sticky-header
                            thead-tr-class="sticky-top"
                            striped
                            hover
                            :per-page="perPage"
                            :current-page="currentPage"
                            :fields="getFields(metaContent)"
                            :items="getItems(dataContent.item_data, metaContent)" />
                        <b-pagination
                            v-model="currentPage"
                            align="center"
                            :total-rows="getItems(dataContent.item_data, metaContent).length"
                            :per-page="perPage"
                            aria-controls="tabular-dataset-table" />
                    </div>
                    <pre v-else :class="{ 'embedded-dataset': !expanded, 'embedded-dataset-expanded': expanded }">
                        <code class="word-wrap-normal">{{ dataContent.item_data }}</code>
                    </pre>
                </div>
                <div v-else>No content found.</div>
                <b-link v-if="dataContent?.truncated" :href="dataContent?.item_url"> Show More... </b-link>
            </div>
        </b-card-body>
    </b-card>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";

import { getAppRoot } from "@/onload/loadConfig";
import { useDatasetStore } from "@/stores/datasetStore";
import { useDatasetTextContentStore } from "@/stores/datasetTextContentStore";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";

import HistoryDatasetAsImage from "./HistoryDatasetAsImage.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Dataset {
    name?: string;
    extension?: string;
    metadata_column_names?: Array<string>;
    metadata_columns?: number;
    metadata_delimiter?: string;
    metadata_comment_lines?: number;
}

// Props
const props = defineProps<{
    datasetId: string;
    embedded?: boolean;
}>();

// Reactive state
const currentPage = ref(1);
const expanded = ref(false);
const perPage = ref(100);

// Store
const { getDatasetError, getDataset } = useDatasetStore();
const {
    getItemById: getContentById,
    getItemLoadError: getContentLoadError,
    isLoadingItem: isLoadingContent,
} = useDatasetTextContentStore();

// Dataset Mapper Store
const datatypesMapperStore = useDatatypesMapperStore();
const { datatypesMapper, loading: datatypesLoading } = storeToRefs(datatypesMapperStore);
const { createMapper } = datatypesMapperStore;

// Computed
const expandable = computed(
    () =>
        metaType.value &&
        !datatypesMapper.value?.isSubTypeOfAny(metaType.value, [
            "tabular",
            "galaxy.datatypes.images.Image",
            "pdf",
            "html",
        ])
);
const dataContent = computed(() => getContentById(props.datasetId));
const dataError = computed(() => getContentLoadError(props.datasetId));
const dataLoading = computed(() => isLoadingContent(props.datasetId));
const downloadUrl = computed(() => `${getAppRoot()}dataset/display?dataset_id=${props.datasetId}`);
const displayUrl = computed(() => `${getAppRoot()}datasets/${props.datasetId}/display/?preview=True`);
const importUrl = computed(() => `${getAppRoot()}dataset/imp?dataset_id=${props.datasetId}`);
const metaContent = computed(() => getDataset(props.datasetId) as Dataset);
const metaError = computed(() => getDatasetError(props.datasetId));
const metaType = computed(() => metaContent.value?.extension);

const getFields = (metaContent: Dataset) => {
    const fields = [];
    const columnNames = metaContent.metadata_column_names || [];
    const columnCount = metaContent.metadata_columns || 0;
    for (let i = 0; i < columnCount; i++) {
        fields.push({
            key: `${i}`,
            label: columnNames[i] || i,
            sortable: true,
        });
    }
    return fields;
};

const getItems = (textData: string, metaData: Dataset) => {
    const tableData: any[] = [];
    const delimiter = metaData.metadata_delimiter || "\t";
    const comments = metaData.metadata_comment_lines || 0;
    const lines = textData.split("\n");
    lines.forEach((line, i) => {
        if (i >= comments) {
            const tabs = line.split(delimiter);
            const rowData: Record<string, string> = {};
            let hasData = false;
            tabs.forEach((cellData, j) => {
                const cellDataTrimmed = cellData.trim();
                if (cellDataTrimmed) {
                    hasData = true;
                }
                rowData[j] = cellDataTrimmed;
            });
            if (hasData) {
                tableData.push(rowData);
            }
        }
    });
    return tableData;
};

const onExpand = () => {
    expanded.value = !expanded.value;
};

// Lifecycle hooks
onMounted(() => {
    createMapper();
});
</script>

<style>
.embedded-dataset {
    height: 10rem;
}
.embedded-dataset-expanded {
    height: 30rem;
}
</style>
