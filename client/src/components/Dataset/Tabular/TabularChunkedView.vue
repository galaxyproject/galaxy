<script setup lang="ts">
import { useWindowScroll } from "@vueuse/core";
import axios from "axios";
import { parse } from "csv-parse/sync";
import { computed, onMounted, reactive, ref, watch } from "vue";

import type { HDADetailed } from "@/api";
import type { TableField } from "@/components/Common/GTable.types";
import { getAppRoot } from "@/onload/loadConfig";

import GTable from "@/components/Common/GTable.vue";

interface TabularChunk {
    ck_data: string;
    offset: number;
    data_line_offset: number;
    column_names?: (string | null)[];
}

interface TabularDataset extends HDADetailed {
    metadata_columns?: number;
    metadata_column_types?: string[];
    metadata_column_names?: string[];
}

interface TabularChunkedViewProps {
    options: TabularDataset;
}

const props = defineProps<TabularChunkedViewProps>();

const offset = ref(0);
const loading = ref(true);
// TODO: add visual loading indicator
const atEOF = ref(false);

const tabularData = reactive<{ rows: string[][] }>({
    rows: [],
});

// Column names from the server, the same ones the dataset peek shows. Every chunk carries them.
const chunkColumnNames = ref<(string | null)[]>();

const columns = computed(() => {
    const columns = Array(props.options.metadata_columns);
    const columnNames = chunkColumnNames.value ?? props.options.metadata_column_names ?? [];
    columnNames.forEach((columnName, index) => {
        columns[index] = columnName ?? undefined;
    });
    return columns;
});

const columnStyle = computed(() => {
    const columnStyle = Array(props.options.metadata_columns);
    if (props.options.metadata_column_types && props.options.metadata_column_types?.length > 0) {
        props.options.metadata_column_types.forEach((column_type, index) => {
            columnStyle[index] = column_type === "str" || column_type === "list" ? "text-left" : "text-right";
        });
    }
    return columnStyle;
});

const fieldKeys = computed(() => {
    return Array.from({ length: columns.value.length }, (_, index) => `column_${index}`);
});

const headers = computed(() => {
    return fieldKeys.value.map((key, index) => {
        const name = columns.value[index];
        const label = name ? `Column ${index + 1}: ${name}` : `Column ${index + 1}`;
        return { key, number: index + 1, name, title: `${label}. Galaxy metadata, not part of the file.` };
    });
});

function headSlot(key: string) {
    return `head(${key})`;
}

const fields = computed<TableField[]>(() => {
    return fieldKeys.value.map((key, index) => ({
        key,
        // same "1.name" / "1" labels as the dataset peek, for every datatype
        label: columns.value[index] ? `${index + 1}.${columns.value[index]}` : `${index + 1}`,
        headerClass: "column-index-header",
        cellClass: columnStyle.value[index],
    }));
});

const tableRows = computed(() => {
    return tabularData.rows.map((row) => {
        const paddedRow =
            row.length < columns.value.length ? row.concat(Array(columns.value.length - row.length).fill("")) : row;

        return Object.fromEntries(fieldKeys.value.map((key, index) => [key, paddedRow[index] ?? ""]));
    });
});

const delimiter = computed(() => {
    return props.options.file_ext === "csv" ? "," : "\t";
});

const chunkUrl = computed(() => {
    return `${getAppRoot()}dataset/display?dataset_id=${props.options.id}`;
});

// Loading more data on user scroll to (near) bottom.
const { y } = useWindowScroll();

watch(y, (newY) => {
    if (
        atEOF.value !== true &&
        loading.value === false &&
        newY > document.body.scrollHeight - window.innerHeight - 100
    ) {
        nextChunk();
    }
});

function processChunk(chunk: TabularChunk) {
    if (chunk.column_names) {
        chunkColumnNames.value = chunk.column_names;
    }
    // parsedChunk is a 2d array of strings
    let parsedChunk = [];
    try {
        parsedChunk = parse(chunk.ck_data, { delimiter: delimiter.value, relax_quotes: true });
    } catch (error) {
        // If this blows up it's likely data in a comment or header line
        // (e.g. VCF files) so just split it by newline first then parse
        // each line individually.
        parsedChunk = chunk.ck_data.trim().split("\n");
        parsedChunk = parsedChunk.map((line) => {
            try {
                const parsedLine = parse(line, { delimiter: delimiter.value })[0];
                return parsedLine || [line];
            } catch (error) {
                // Failing lines get passed through intact for row-level
                // rendering/parsing.
                return [line];
            }
        });
    }
    parsedChunk.forEach((row: string[], index: number) => {
        if (index >= (chunk.data_line_offset || 0)) {
            // TODO test perf of a batch update instead of individual row pushes?
            tabularData.rows.push(processRow(row));
        }
    });
    // update new offset
    offset.value = chunk.offset;
}

function processRow(row: string[]) {
    const num_columns = columns.value.length;
    if (row.length === num_columns) {
        // pass through
        return row;
    } else if (row.length > num_columns) {
        // SAM file or like format with optional metadata included.
        return row.slice(0, num_columns - 1).concat([row.slice(num_columns - 1).join("\t")]);
    } else if (row.length === 1) {
        // Try to split by comma first
        let rowDataSplit = row[0]!.split(",");
        if (rowDataSplit.length === num_columns) {
            return rowDataSplit;
        }
        // Try to split by tab
        rowDataSplit = row[0]!.split("\t");
        if (rowDataSplit.length === num_columns) {
            return rowDataSplit;
        }
        // Try to split by space
        rowDataSplit = row[0]!.split(" ");
        if (rowDataSplit.length === num_columns) {
            return rowDataSplit;
        }
        return row;
    } else {
        // rowData.length is greater than one, but less than num_columns.  Render cells and pad tds.
        // Possibly a SAM file or like format with optional metadata missing.
        // Could also be a tabular file with a line with missing columns.
        return row.concat(Array(num_columns - row.length).fill(""));
    }
}

function nextChunk() {
    // Attempt to fetch next chunk, given the current offset.
    loading.value = true;
    axios
        .get(chunkUrl.value, {
            params: {
                offset: offset.value,
            },
        })
        .then((response) => {
            if (response.data.ck_data === "") {
                // Galaxy returns an empty chunk if there's no more.
                atEOF.value = true;
            } else {
                // Otherwise process the chunk.
                processChunk(response.data);
            }
            loading.value = false;
        });
}

onMounted(() => {
    // Fetch and render first chunk
    nextChunk();
});
</script>

<template>
    <div>
        <!-- TODO loading spinner locked to top right -->
        <GTable compact hover striped :fields="fields" :items="tableRows" :load-more-loading="loading">
            <!-- same markup as column_index_header_cell() in lib/galaxy/datatypes/tabular.py -->
            <template v-for="header in headers" v-slot:[headSlot(header.key)]>
                <span :key="header.key" class="column-index" :title="header.title">
                    <span class="column-number">{{ header.number }}</span>
                    <span v-if="header.name" class="column-name">{{ header.name }}</span>
                </span>
            </template>
        </GTable>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

// Same look as the dataset peek header (see %column-index-header in dataset.scss):
// Galaxy's column index, not a header line from the file.
:deep(.g-table thead th.column-index-header) {
    color: $text-muted;
    background: $gray-300;
    font-weight: normal;
    border-bottom: 1px solid $border-color;
    border-right: 1px solid $border-color;
    // not a line of the file, so keep it out of copied text
    user-select: none;

    &:last-child {
        border-right: none;
    }
    padding: 0.25rem 0.75rem;
    font-size: 0.85em;
}
:deep(.g-table tbody td) {
    border-right: 1px solid $gray-300;

    &:last-child {
        border-right: none;
    }
}
</style>
