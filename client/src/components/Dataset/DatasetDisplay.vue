<script setup lang="ts">
import axios from "axios";
import { onMounted, ref } from "vue";

import { withPrefix } from "@/utils/redirect";

import TabularChunkedView from "components/Visualizations/Tabular/TabularChunkedView.vue";

const MAX_PEEK_SIZE_BINARY = 100000;

interface Props {
    datasetId: string;
    isPreview: boolean;
}

const props = withDefaults(defineProps<Props>(), {});

const content = ref();
const datasetDetails = ref();

onMounted(async () => {
    const detailsUrl = withPrefix(`/api/datasets/${props.datasetId}`);
    try {
        const { data } = await axios.get(detailsUrl);
        datasetDetails.value = data;
    } catch (e) {
        console.error(e);
    }

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
    <div v-if="datasetDetails">
        <div v-if="datasetDetails.deleted" id="deleted-data-message" class="errormessagelarge">
            You are viewing a deleted dataset.
        </div>
        <div class="warningmessagelarge">
            This dataset is large and only the first megabyte is shown below.<br />
            <a href="${h.url_for( controller='dataset', action='display', dataset_id=trans.security.encode_id( data.id ), filename='' )}">Show all</a> |
            <a href="${h.url_for( controller='dataset', action='display', dataset_id=trans.security.encode_id( data.id ), to_ext=data.ext )}">Save</a>
        </div>
        <div class="warningmessagelarge">
            This is a binary (or unknown to Galaxy) dataset of size ${ file_size }. Preview is not implemented for this filetype. Displaying
            <span v-if="datasetDetails.file_size > MAX_PEEK_SIZE_BINARY">
                first 100KB
            </span>
            as ASCII text<br/>
            <a href="${h.url_for( controller='dataset', action='display', dataset_id=trans.security.encode_id( data.id ), to_ext=data.ext )}">Download</a>
        </div>
        <TabularChunkedView v-if="content && content.ck_data" :options="{ dataset_config: { ...datasetDetails, first_data_chunk: content } }" />
        <pre v-else>
            {{ content }}
        </pre>
    </div>
</template>

