<script setup lang="ts">
import { useWindowScroll } from "@vueuse/core";
import axios from "axios";
import { parse } from "csv-parse/sync";
import { computed, onMounted, reactive, ref, watch } from "vue";

import { getAppRoot } from "@/onload/loadConfig";

interface TabularChunk {
    ck_data: string;
    offset: number;
    data_line_offset: number;
}

interface TabularChunkedViewProps {
    options: {
        dataset_config: {
            id: string;
            file_ext: string;
            first_data_chunk: TabularChunk;
            metadata_columns: number;
            metadata_column_types: string[];
            metadata_column_names: string[];
        };
    };
}

const props = defineProps<TabularChunkedViewProps>();

const offset = ref(0);
const loading = ref(true);
// TODO: add visual loading indicator
const atEOF = ref(false);

const tabularData = reactive<{ rows: string[][] }>({
    rows: [],
});

const columns = computed(() => {
    const columns = Array(props.options.dataset_config.metadata_columns);
    // for each column_name, inject header
    if (props.options.dataset_config.metadata_column_names?.length > 0) {
        props.options.dataset_config.metadata_column_names.forEach((column_name, index) => {
            columns[index] = column_name;
        });
    }
    return columns;
});

const columnStyle = computed(() => {
    const columnStyle = Array(props.options.dataset_config.metadata_columns);
    if (props.options.dataset_config.metadata_column_types?.length > 0) {
        props.options.dataset_config.metadata_column_types.forEach((column_type, index) => {
            columnStyle[index] = column_type === "str" || column_type === "list" ? "string-align" : "number-align";
        });
    }
    return columnStyle;
});

const delimiter = computed(() => {
    return props.options.dataset_config.file_ext === "csv" ? "," : "\t";
});

const chunkUrl = computed(() => {
    return `${getAppRoot()}dataset/display?dataset_id=${props.options.dataset_config.id}`;
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
    // Render first chunk if available.
    if (props.options.dataset_config.first_data_chunk) {
        processChunk(props.options.dataset_config.first_data_chunk);
        loading.value = false;
    }
});
</script>

<template>
    <div>
        <!-- TODO loading spinner locked to top right -->
        <b-table-simple hover small striped>
            <b-thead head-variant="dark">
                <b-tr>
                    <b-th v-for="(column, index) in columns" :key="column">{{ column || `列 ${index + 1}` }}</b-th>
                </b-tr>
            </b-thead>
            <b-tbody>
                <b-tr v-for="(row, index) in tabularData.rows" :key="index">
                    <b-td
                        v-for="(element, elementIndex) in row.slice(0, -1)"
                        :key="elementIndex"
                        :class="columnStyle[elementIndex]">
                        {{ element }}
                    </b-td>
                    <b-td :class="columnStyle[row.length - 1]" :colspan="1 + columns.length - row.length">
                        {{ row.slice(-1)[0] }}
                    </b-td>
                </b-tr>
            </b-tbody>
        </b-table-simple>
    </div>
</template>

<style lang="scss" scoped>
.string-align {
    text-align: left;
}
.number-align {
    text-align: right;
}
</style>
