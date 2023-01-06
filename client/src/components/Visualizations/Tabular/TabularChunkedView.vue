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
            // NOT COMPLETE
        };
    };
}

const { y } = useWindowScroll();

watch(y, (newY) => {
    if (loading.value === false && newY > document.body.scrollHeight - window.innerHeight - 100) {
        nextChunk();
    }
});

const props = defineProps<TabularChunkedViewProps>();

const offset = ref(0);

const tabularData = reactive<{ columns: string[]; rows: string[] }>({
    columns: [],
    rows: [],
});

const loading = ref(true);

const delimiter = computed(() => {
    return props.options.dataset_config.file_ext === "csv" ? "," : "\t";
});
const chunkUrl = computed(() => {
    return `${getAppRoot()}dataset/display?dataset_id=${props.options.dataset_config.id}`;
});

// const columns = computed(() => {
//     return props.options.headers;
// });

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
    parsedChunk.forEach((row: any, index: Number) => {
        if (index >= (chunk.data_line_offset || 0)) {
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
    // Wait 2 seconds, then fetch another chunk
    // setTimeout(() => {
    //     nextChunk();
    // }, 2000);
});
</script>

<template>
    <div>
        <!-- TODO loading spinner locked to top right -->
        <b-table-simple hover small striped>
            <b-thead head-variant="dark">
                <b-tr>
                    <b-th v-for="column in tabularData.columns" :key="column">{{ column }}</b-th>
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
