<script setup lang="ts">
import axios from "axios";
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useDatasetStore } from "@/stores/datasetStore";
import { useUserStore } from "@/stores/userStore";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";
import { bytesToString } from "@/utils/utils";

import Alert from "components/Alert.vue";
import LoadingSpan from "components/LoadingSpan.vue";
import TabularChunkedView from "components/Visualizations/Tabular/TabularChunkedView.vue";

interface Props {
    datasetId: string;
    isBinary: boolean;
}

const { getDataset, isLoadingDataset } = useDatasetStore();

const props = defineProps<Props>();

const content = ref();
const errorMessage = ref();
const sanitizedImport = ref(false);
const sanitizedToolId = ref();
const truncated = ref();

const { isAdmin } = storeToRefs(useUserStore());

const dataset = computed(() => getDataset(props.datasetId));
const datasetUrl = computed(() => withPrefix(`/dataset/display?dataset_id=${props.datasetId}`));
const downloadUrl = computed(() => withPrefix(`${datasetUrl.value}&to_ext=${dataset.value?.file_ext}`));
const isLoading = computed(() => isLoadingDataset(props.datasetId));

const sanitizedMessage = computed(() => {
    const plainText = "Contents are shown as plain text.";
    if (sanitizedImport.value) {
        return `Dataset has been imported. ${plainText}`;
    } else if (sanitizedToolId.value) {
        return `Dataset created by a tool that is not known to create safe HTML. ${plainText}`;
    }
    return undefined;
});

watch(
    () => props.datasetId,
    async () => {
        const url = withPrefix(`/datasets/${props.datasetId}/display/?preview=True`);
        try {
            const { data, headers } = await axios.get(url);
            content.value = data;
            truncated.value = headers["x-content-truncated"];
            sanitizedImport.value = !!headers["x-sanitized-job-imported"];
            sanitizedToolId.value = headers["x-sanitized-tool-id"];
            errorMessage.value = "";
        } catch (e) {
            errorMessage.value = errorMessageAsString(e);
            console.error(e);
        }
    },
    { immediate: true },
);
</script>

<template>
    <BAlert v-if="errorMessage" variant="danger" show>
        {{ errorMessage }}
    </BAlert>
    <LoadingSpan v-else-if="isLoading || !dataset" message="Loading dataset content" />
    <div v-else>
        <Alert v-if="sanitizedMessage" :dismissible="true" variant="warning" data-description="sanitization warning">
            {{ sanitizedMessage }}
            <span v-if="isAdmin && sanitizedToolId">
                <br />
                <router-link data-description="allowlist link" to="/admin/sanitize_allow">Review Allowlist</router-link>
                if outputs of {{ sanitizedToolId }} are trusted and should be shown as HTML.
            </span>
        </Alert>
        <div v-if="dataset.deleted" id="deleted-data-message" class="errormessagelarge">
            You are viewing a deleted dataset.
        </div>
        <TabularChunkedView v-if="content && content.ck_data" :options="{ ...dataset, first_data_chunk: content }" />
        <div v-else-if="content">
            <div v-if="isBinary">
                This is a binary (or unknown to Galaxy) dataset of size {{ bytesToString(dataset.file_size) }}. Preview
                is not implemented for this filetype. Displaying as ASCII text.
            </div>
            <div v-if="truncated" class="warningmessagelarge">
                <div>This dataset is large and only the first {{ bytesToString(truncated) }} is shown below.</div>
                <a :href="downloadUrl">Download</a>
            </div>
            <pre v-if="sanitizedMessage || sanitizedToolId">{{ content }}</pre>
            <pre v-else v-html="content" />
        </div>
    </div>
</template>
