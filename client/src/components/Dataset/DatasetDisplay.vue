<script setup lang="ts">
import axios from "axios";
import { onMounted, ref } from "vue";
import { withPrefix } from "@/utils/redirect";

interface Props {
    datasetId: string;
    isPreview: boolean;
}

const props = withDefaults(defineProps<Props>(), {});

const content = ref();
const deleted = ref(true);

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
    <div>
        <div v-if="deleted" class="errormessagelarge" id="deleted-data-message">
            You are viewing a deleted dataset.
        </div>
        <div class="warningmessagelarge">
            This dataset is large and only the first megabyte is shown below.<br />
            <a href="${h.url_for( controller='dataset', action='display', dataset_id=trans.security.encode_id( data.id ), filename='' )}">Show all</a> |
            <a href="${h.url_for( controller='dataset', action='display', dataset_id=trans.security.encode_id( data.id ), to_ext=data.ext )}">Save</a>
        </div>
        <div class="warningmessagelarge">
            This is a binary (or unknown to Galaxy) dataset of size ${ file_size }. Preview is not implemented for this filetype. Displaying
            %if truncated:
        first 100KB
            %endif
        as ASCII text<br/>
            <a href="${h.url_for( controller='dataset', action='display', dataset_id=trans.security.encode_id( data.id ), to_ext=data.ext )}">Download</a>
        </div>
        <pre>
            {{  content }}
        </pre>
    </div>
</template>

