<template>
    <UrlDataProvider v-slot="{ result: metaData, loading: metaLoading, error: metaError }" :url="metaUrl">
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
                        v-if="expanded"
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
                        v-else
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
                    <span class="font-weight-light">{{ metaData?.name }}</span>
                </span>
            </b-card-header>
            <b-card-body>
                <UrlDataProvider
                    v-slot="{ result: itemContent, loading: datasetLoading, error }"
                    :key="itemUrl"
                    :url="itemUrl">
                    <LoadingSpan v-if="datasetLoading" message="Loading Dataset" />
                    <LoadingSpan v-else-if="datatypesMapperStore.loading" message="Loading Datatypes" />
                    <div v-else-if="error">{{ error }}</div>
                    <div v-else-if="!datatypesMapper">Datatypes not loaded.</div>
                    <div v-else :class="contentClass(metaData?.ext)">
                        <b-embed
                            v-if="datatypesMapper.isSubTypeOfAny(metaData?.ext, ['pdf', 'html'])"
                            type="iframe"
                            aspect="16by9"
                            :src="displayUrl" />
                        <HistoryDatasetAsImage
                            v-else-if="datatypesMapper.isSubTypeOfAny(metaData?.ext, ['galaxy.datatypes.images.Image'])"
                            :dataset-id="datasetId" />
                        <div v-else-if="itemContent.item_data">
                            <div v-if="datatypesMapper.isSubTypeOfAny(metaData?.ext, ['tabular'])">
                                <LoadingSpan v-if="metaLoading" message="Loading Metadata" />
                                <div v-else-if="metaError">{{ metaError }}</div>
                                <div v-else>
                                    <b-table
                                        id="tabular-dataset-table"
                                        sticky-header
                                        thead-tr-class="sticky-top"
                                        striped
                                        hover
                                        :per-page="perPage"
                                        :current-page="currentPage"
                                        :fields="getFields(metaData)"
                                        :items="getItems(itemContent.item_data, metaData)" />
                                    <b-pagination
                                        v-model="currentPage"
                                        align="center"
                                        :total-rows="getItems(itemContent.item_data, metaData).length"
                                        :per-page="perPage"
                                        aria-controls="tabular-dataset-table" />
                                </div>
                            </div>
                            <pre v-else>
                                <code class="word-wrap-normal">{{ itemContent.item_data }}</code>
                            </pre>
                        </div>
                        <div v-else>No content found.</div>
                        <b-link v-if="itemContent.truncated" :href="itemContent.item_url"> Show More... </b-link>
                    </div>
                </UrlDataProvider>
            </b-card-body>
        </b-card>
    </UrlDataProvider>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { UrlDataProvider } from "@/components/providers/UrlDataProvider";
import { getAppRoot } from "@/onload/loadConfig";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";

import HistoryDatasetAsImage from "./HistoryDatasetAsImage.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

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
const datatypesMapperStore = useDatatypesMapperStore();
const { datatypesMapper } = datatypesMapperStore;

// Computed
const downloadUrl = computed(() => `${getAppRoot()}dataset/display?dataset_id=${props.datasetId}`);
const displayUrl = computed(() => `${getAppRoot()}datasets/${props.datasetId}/display/?preview=True`);
const importUrl = computed(() => `${getAppRoot()}dataset/imp?dataset_id=${props.datasetId}`);
const itemUrl = computed(() => `/api/datasets/${props.datasetId}/get_content_as_text`);
const metaUrl = computed(() => `/api/datasets/${props.datasetId}`);

// Methods
const contentClass = (datasetType: string) => {
    if (datatypesMapper?.isSubTypeOfAny(datasetType, ["tabular"])) {
        return "";
    }
    return expanded.value ? "embedded-dataset-expanded" : "embedded-dataset";
};

const getFields = (metaData: any) => {
    const fields = [];
    const columnNames = metaData.metadata_column_names || [];
    const columnCount = metaData.metadata_columns;
    for (let i = 0; i < columnCount; i++) {
        fields.push({
            key: `${i}`,
            label: columnNames[i] || i,
            sortable: true,
        });
    }
    return fields;
};

const getItems = (textData: string, metaData: any) => {
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
    datatypesMapperStore.createMapper();
});
</script>
