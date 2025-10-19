<script setup lang="ts">
import axios from "axios";
import { computed, onMounted, ref } from "vue";

import { withPrefix } from "@/utils/redirect";
import { bytesToString } from "@/utils/utils";

import TabularChunkedView from "components/Visualizations/Tabular/TabularChunkedView.vue";
import { useDatasetStore } from "@/stores/datasetStore";

interface Props {
    datasetId: string;
    isBinary: boolean;
}

const MAX_PEEK_SIZE_BINARY = 100000;

const { getDataset, isLoadingDataset } = useDatasetStore();

const props = withDefaults(defineProps<Props>(), {});

const content = ref();

const dataset = computed(() => getDataset(props.datasetId));
const datasetUrl = computed(() => withPrefix(`/dataset/display?dataset_id=${props.datasetId}`));
const downloadUrl = computed(() =>withPrefix(`${datasetUrl.value}&to_ext=${dataset.value?.file_ext}`),);
const isLoading = computed(() => isLoadingDataset(props.datasetId));

onMounted(async () => {
    const url = withPrefix(`/datasets/${props.datasetId}/display/?preview=True`);
    try {
        const { data } = await axios.get(url);
        content.value = data;
    } catch (e) {
        console.error(e);
    }
});
</script>

<template>
    <div v-if="!isLoading && dataset">
        <div v-if="dataset.deleted" id="deleted-data-message" class="errormessagelarge">
            You are viewing a deleted dataset.
        </div>
        <div class="warningmessagelarge">
            <span>
                This dataset is large and only the first megabyte is shown below.<br />
            </span>
            <span>
                This is a binary (or unknown to Galaxy) dataset of size {{ bytesToString(dataset.file_size) }}.
                Preview is not implemented for this filetype. Displaying
                <span v-if="dataset.file_size > MAX_PEEK_SIZE_BINARY"> first 100KB </span>
                as ASCII text<br />
            </span>
            <a :href="downloadUrl">Download</a>
        </div>
        <TabularChunkedView
            v-if="content && content.ck_data"
            :options="{ dataset_config: { ...dataset, first_data_chunk: content } }" />
        <pre v-else>
            {{ content }}
        </pre>
    </div>
</template>
