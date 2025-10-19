<script setup lang="ts">
import axios from "axios";
import { computed, onMounted, ref } from "vue";

import { useDatasetStore } from "@/stores/datasetStore";
import { withPrefix } from "@/utils/redirect";
import { bytesToString } from "@/utils/utils";

import TabularChunkedView from "components/Visualizations/Tabular/TabularChunkedView.vue";

interface Props {
    datasetId: string;
    isBinary: boolean;
}

const { getDataset, isLoadingDataset } = useDatasetStore();

const props = defineProps<Props>();

const content = ref();

const contentLength = computed(() => (typeof content.value === "string" ? content.value?.length : 0));
const dataset = computed(() => getDataset(props.datasetId));
const datasetUrl = computed(() => withPrefix(`/dataset/display?dataset_id=${props.datasetId}`));
const downloadUrl = computed(() => withPrefix(`${datasetUrl.value}&to_ext=${dataset.value?.file_ext}`));
const isLoading = computed(() => isLoadingDataset(props.datasetId));
const isTruncated = computed(() => dataset.value && dataset.value.file_size > contentLength.value);

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
        <TabularChunkedView
            v-if="content && content.ck_data"
            :options="{ dataset_config: { ...dataset, first_data_chunk: content } }" />
        <div v-else-if="content">
            <div v-if="isBinary">
                This is a binary (or unknown to Galaxy) dataset of size {{ bytesToString(dataset.file_size) }}. Preview
                is not implemented for this filetype. Displaying as ASCII text.
            </div>
            <div v-if="isTruncated" class="warningmessagelarge">
                <div>
                    This dataset is large and only the first <span> {{ bytesToString(contentLength) }} </span> is shown
                    below.
                </div>
                <a :href="downloadUrl">Download</a>
            </div>
            <pre>
                {{ content }}
            </pre>
        </div>
    </div>
</template>
