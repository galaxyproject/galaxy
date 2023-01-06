<script setup lang="ts">
import axios from "axios";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { parse } from "csv-parse/sync";
import { getAppRoot } from "@/onload/loadConfig";
import { useWindowScroll } from "@vueuse/core";

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
            metadata_column_names: null | string[];
            // metadata_data_lines: number,
            // metadata_comment_lines: null | number,
            // INCOMPLETE
        };
    };
}

const props = defineProps<TabularChunkedViewProps>();

const offset = ref(0);
const loading = ref(true);

const tabularData = reactive<{ columns: string[]; rows: string[][] }>({
    columns: [],
    rows: [],
});

const delimiter = computed(() => {
    return props.options.dataset_config.file_ext === "csv" ? "," : "\t";
});
const chunkUrl = computed(() => {
    return `${getAppRoot()}dataset/display?dataset_id=${props.options.dataset_config.id}`;
});

const { y } = useWindowScroll();
watch(y, (newY) => {
    if (loading.value === false && newY > document.body.scrollHeight - window.innerHeight - 100) {
        nextChunk();
    }
});

function processChunk(chunk: TabularChunk) {
    // parsedChunk is a 2d array of strings
    let parsedChunk = [];
    try {
        parsedChunk = parse(chunk.ck_data, { delimiter: delimiter.value });
    } catch (error) {
        // If this blows up it's likely data in a comment or header line
        // (e.g. VCF files) so just split it by newline first then parse
        // each line individually.
        parsedChunk = chunk.ck_data.trim().split("\n");
        parsedChunk = parsedChunk.map((line) => {
            try {
                return parse(line, { delimiter: delimiter.value })[0];
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
            tabularData.rows.push(row);
        }
    });
    // update new offset
    offset.value = chunk.offset;
}

function nextChunk() {
    loading.value = true;
    axios
        .get(chunkUrl.value, {
            params: {
                offset: offset.value,
            },
        })
        .then((response) => {
            processChunk(response.data);
            loading.value = false;
        });
}

onMounted(() => {
    if (props.options.dataset_config.first_data_chunk) {
        processChunk(props.options.dataset_config.first_data_chunk);
        loading.value = false;
    }
    const columnNames = props.options.dataset_config.metadata_column_names;
    if (columnNames !== null) {
        tabularData.columns = columnNames;
    }
    else {
        tabularData.columns = Array(props.options.dataset_config.metadata_columns);
    }
});
</script>

<template>
    <div>
        <!-- TODO loading spinner locked to top right -->
        <b-table-simple hover small striped>
            <b-thead head-variant="dark">
                <b-tr>
                    <b-th v-for="(column, index) in tabularData.columns" :key="column">{{ column || index + 1 }}</b-th>
                </b-tr>
            </b-thead>
            <b-tbody>
                <b-tr v-for="(row, index) in tabularData.rows" :key="index">
                    <b-td v-for="element in row" :key="element">{{ element }}</b-td>
                </b-tr>
            </b-tbody>
        </b-table-simple>
    </div>
</template>

<style lang="scss" scoped></style>
