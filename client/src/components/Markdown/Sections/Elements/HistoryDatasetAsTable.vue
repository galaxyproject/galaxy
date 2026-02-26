<script setup lang="ts">
import { BCard, BCardFooter, BCardTitle } from "bootstrap-vue";
import { computed } from "vue";

import type { TableField } from "@/components/Common/GTable.types";
import { UrlDataProvider } from "@/components/providers/UrlDataProvider.js";

import GLink from "@/components/BaseComponents/GLink.vue";
import GTable from "@/components/Common/GTable.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface HistoryDatasetAsTableProps {
    compact: boolean;
    datasetId: string;
    footer?: string;
    showColumnHeaders: boolean;
    title?: string;
    path?: string;
}

const props = withDefaults(defineProps<HistoryDatasetAsTableProps>(), {
    compact: false,
    showColumnHeaders: true,
    title: undefined,
    footer: undefined,
    path: undefined,
});

const itemUrl = computed(() => {
    if (props.path) {
        return `/api/datasets/${props.datasetId}/get_content_as_text?filename=${props.path}`;
    } else {
        return `/api/datasets/${props.datasetId}/get_content_as_text`;
    }
});

const metaUrl = computed(() => {
    return `/api/datasets/${props.datasetId}`;
});

const expanded = false;

const contentClass = computed(() => {
    if (expanded) {
        return "embedded-dataset-expanded";
    } else {
        return "embedded-dataset";
    }
});

function getFields(metaData: any): TableField[] {
    const fields: TableField[] = [];
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
    const tableData: Record<string, string>[] = [];
    const delimiter: string = metaData.metadata_delimiter || "\t";
    const comments: number = metaData.metadata_comment_lines || 0;
    const lines = textData.split("\n");
    lines.forEach((line: string, i: number) => {
        if (i >= comments) {
            const tabs = line.split(delimiter);
            const rowData: Record<string, string> = {};
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
    <BCard :no-body="props.compact">
        <BCardTitle v-if="title">
            <b>{{ title }}</b>
        </BCardTitle>

        <UrlDataProvider v-slot="{ result: itemContent, loading, error }" :url="itemUrl">
            <LoadingSpan v-if="loading" message="Loading Dataset" />
            <div v-else-if="error">{{ error }}</div>
            <div v-else :class="contentClass">
                <div v-if="itemContent.item_data">
                    <UrlDataProvider
                        v-slot="{ result: metaData, loading: metaLoading, error: metaError }"
                        :url="metaUrl">
                        <LoadingSpan v-if="metaLoading" message="Loading Metadata" />
                        <div v-else-if="metaError">{{ metaError }}</div>
                        <GTable
                            v-else
                            :hide-header="!props.showColumnHeaders"
                            striped
                            hover
                            :fields="getFields(metaData)"
                            :items="getItems(itemContent.item_data, metaData)" />
                    </UrlDataProvider>
                </div>
                <div v-else>No content found.</div>

                <GLink v-if="itemContent.truncated" :href="itemContent.item_url"> Show More... </GLink>
            </div>
        </UrlDataProvider>
        <BCardFooter v-if="footer">
            {{ footer }}
        </BCardFooter>
    </BCard>
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
