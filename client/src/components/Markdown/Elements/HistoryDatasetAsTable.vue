<script setup lang="ts">
import { computed } from "vue";

import { UrlDataProvider } from "@/components/providers/UrlDataProvider.js";

import LoadingSpan from "@/components/LoadingSpan.vue";

interface HistoryDatasetAsTableProps {
    historyDatasetId: string;
    compact: boolean;
    showColumnHeaders: boolean;
    title?: string;
    footer?: string;
}

const props = withDefaults(defineProps<HistoryDatasetAsTableProps>(), {
    compact: false,
    showColumnHeaders: true,
    title: undefined,
    footer: undefined,
});

const itemUrl = computed(() => {
    return `/api/datasets/${props.historyDatasetId}/get_content_as_text`;
});

const metaUrl = computed(() => {
    return `/api/datasets/${props.historyDatasetId}`;
});

const expanded = false;

const contentClass = computed(() => {
    if (expanded) {
        return "embedded-dataset-expanded";
    } else {
        return "embedded-dataset";
    }
});

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

function getItems(textData: any, metaData: any) {
    const tableData: object[] = [];
    const delimiter: string = metaData.metadata_delimiter || "\t";
    const comments: number = metaData.metadata_comment_lines || 0;
    const lines = textData.split("\n");
    lines.forEach((line: string, i: number) => {
        if (i >= comments) {
            const tabs = line.split(delimiter);
            const rowData: string[] = [];
            let hasData = false;
            tabs.forEach((cellData: string, j: number) => {
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

<template>
    <b-card :no-body="props.compact">
        <b-card-title v-if="title">
            <b>{{ title }}</b>
        </b-card-title>
        <UrlDataProvider v-slot="{ result: itemContent, loading, error }" :url="itemUrl">
            <LoadingSpan v-if="loading" message="Loading Dataset" />
            <div v-else-if="error">{{ error }}</div>
            <div v-else :class="contentClass">
                <div v-if="itemContent.item_data">
                    <div>
                        <UrlDataProvider
                            v-slot="{ result: metaData, loading: metaLoading, error: metaError }"
                            :url="metaUrl">
                            <LoadingSpan v-if="metaLoading" message="Loading Metadata" />
                            <div v-else-if="metaError">{{ metaError }}</div>
                            <b-table
                                v-else
                                :thead-class="props.showColumnHeaders ? '' : 'd-none'"
                                striped
                                hover
                                :fields="getFields(metaData)"
                                :items="getItems(itemContent.item_data, metaData)" />
                        </UrlDataProvider>
                    </div>
                </div>
                <div v-else>No content found.</div>
                <b-link v-if="itemContent.truncated" :href="itemContent.item_url"> Show More... </b-link>
            </div>
        </UrlDataProvider>
        <b-card-footer v-if="footer">
            {{ footer }}
        </b-card-footer>
    </b-card>
</template>

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
