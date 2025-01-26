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
                    <span class="font-weight-light">{{ metaData.name }}</span>
                </span>
            </b-card-header>
            <b-card-body>
                <UrlDataProvider v-slot="{ result: itemContent, loading, error }" :url="itemUrl">
                    <UrlDataProvider v-slot="{ result: datatypesModel, loading: datatypesLoading }" :url="datatypesUrl">
                        <LoadingSpan v-if="loading" message="Loading Dataset" />
                        <LoadingSpan v-else-if="datatypesLoading" message="Loading Datatypes" />
                        <div v-else-if="error">{{ error }}</div>
                        <div v-else :class="contentClass">
                            <b-embed
                                v-if="isSubTypeOfAny(metaData.ext, ['pdf', 'html'], datatypesModel)"
                                type="iframe"
                                aspect="16by9"
                                :src="displayUrl" />
                            <HistoryDatasetAsImage
                                v-else-if="
                                    isSubTypeOfAny(metaData.ext, ['galaxy.datatypes.images.Image'], datatypesModel)
                                "
                                :dataset-id="datasetId" />
                            <div v-else-if="itemContent.item_data">
                                <div v-if="isSubTypeOfAny(metaData.ext, ['tabular'], datatypesModel)">
                                    <LoadingSpan v-if="metaLoading" message="Loading Metadata" />
                                    <div v-else-if="metaError">{{ metaError }}</div>
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
                                </div>
                                <pre v-else>
                                    <code class="word-wrap-normal">{{ itemContent.item_data }}</code>
                                </pre>
                            </div>
                            <div v-else>No content found.</div>
                            <b-link v-if="itemContent.truncated" :href="itemContent.item_url"> Show More... </b-link>
                        </div>
                    </UrlDataProvider>
                </UrlDataProvider>
            </b-card-body>
        </b-card>
    </UrlDataProvider>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

import { DatatypesMapperModel } from "@/components/Datatypes/model";
import { UrlDataProvider } from "@/components/providers/UrlDataProvider";
import { getAppRoot } from "@/onload/loadConfig";

import HistoryDatasetAsImage from "./HistoryDatasetAsImage.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const props = defineProps<{
    datasetId: string;
    embedded?: boolean;
}>();

const expanded = ref(false);

const contentClass = computed(() => (expanded.value ? "embedded-dataset-expanded" : "embedded-dataset"));

const datatypesUrl = computed(() => "/api/datatypes/types_and_mapping");
const downloadUrl = computed(() => `${getAppRoot()}dataset/display?dataset_id=${props.datasetId}`);
const displayUrl = computed(() => `${getAppRoot()}datasets/${props.datasetId}/display/?preview=True`);
const importUrl = computed(() => `${getAppRoot()}dataset/imp?dataset_id=${props.datasetId}`);
const itemUrl = computed(() => `/api/datasets/${props.datasetId}/get_content_as_text`);
const metaUrl = computed(() => `/api/datasets/${props.datasetId}`);

function onExpand() {
    expanded.value = !expanded.value;
}

function isSubTypeOfAny(child: string, parents: string[], datatypesModel: any) {
    const datatypesMapper = new DatatypesMapperModel(datatypesModel);
    return datatypesMapper.isSubTypeOfAny(child, parents);
}

function getFields(metaData: any) {
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
}

function getItems(textData: string, metaData: any) {
    const tableData: any = [];
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
}
</script>

<style scoped>
.embedded-dataset {
    max-height: 20rem;
    overflow-y: auto;
}
.embedded-dataset-expanded {
    max-height: 40rem;
    overflow-y: auto;
}
</style>
