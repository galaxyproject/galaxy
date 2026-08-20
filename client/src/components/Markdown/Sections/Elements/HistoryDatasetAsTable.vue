<script setup lang="ts">
import { BCard, BCardFooter, BCardTitle } from "bootstrap-vue";
import { computed } from "vue";

import type { TableField } from "@/components/Common/GTable.types";
import { UrlDataProvider } from "@/components/providers/UrlDataProvider.js";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GTable from "@/components/Common/GTable.vue";
import ExternalLink from "@/components/ExternalLink.vue";
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

const contentClass = computed(() => (props.compact ? "embedded-dataset" : "embedded-dataset-expanded"));

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
    <BCard :no-body="props.compact" class="my-1">
        <BCardTitle v-if="title" class="p-2">
            <b>{{ title }}</b>
        </BCardTitle>

        <UrlDataProvider v-slot="{ result: itemContent, loading, error }" :url="itemUrl">
            <LoadingSpan v-if="loading" message="Loading Dataset" />
            <GAlert v-else-if="error" variant="danger">{{ error }}</GAlert>
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
                            :compact="props.compact"
                            striped
                            show-empty
                            hover
                            :fields="getFields(metaData)"
                            :items="getItems(itemContent.item_data, metaData)" />
                    </UrlDataProvider>
                </div>
                <div v-else>No content found.</div>

                <ExternalLink v-if="itemContent?.truncated" :href="`/datasets/${props.datasetId}/display`">
                    Show More
                </ExternalLink>
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
