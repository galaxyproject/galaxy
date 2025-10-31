<script setup lang="ts">
import { faExclamationTriangle, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useDatasetStore } from "@/stores/datasetStore";
import { useUserStore } from "@/stores/userStore";
import STATES from "@/utils/datasetStates";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";
import { bytesToString } from "@/utils/utils";

import Alert from "@/components/Alert.vue";
import TabularChunkedView from "@/components/Dataset/Tabular/TabularChunkedView.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import CenterFrame from "@/entry/analysis/modules/CenterFrame.vue";

interface Props {
    datasetId: string;
    isBinary: boolean;
}

const { getDataset, isLoadingDataset } = useDatasetStore();

const emit = defineEmits(["load"]);

const props = defineProps<Props>();

const contentTruncated = ref<number | null>(null);
const contentChunked = ref<boolean>(false);
const errorMessage = ref<string>("");
const sanitizedJobImported = ref<boolean>(false);
const sanitizedToolId = ref<string | null>(null);

const { isAdmin } = storeToRefs(useUserStore());

const dataset = computed(() => getDataset(props.datasetId));
const datasetUrl = computed(() => `/datasets/${props.datasetId}/display`);
const downloadUrl = computed(() => withPrefix(`${datasetUrl.value}?to_ext=${dataset.value?.file_ext}`));
const isLoading = computed(() => isLoadingDataset(props.datasetId));
const previewUrl = computed(() => `${datasetUrl.value}?preview=True`);

const sanitizedMessage = computed(() => {
    const plainText = "Contents are shown as plain text.";
    if (sanitizedJobImported.value) {
        return `Dataset has been imported. ${plainText}`;
    } else if (sanitizedToolId.value) {
        return `Dataset created by a tool that is not known to create safe HTML. ${plainText}`;
    }
    return undefined;
});

watch(
    () => props.datasetId,
    async () => {
        try {
            const { headers } = await fetch(withPrefix(previewUrl.value), { method: "HEAD" });
            contentChunked.value = !!headers.get("x-content-chunked");
            contentTruncated.value = headers.get("x-content-truncated")
                ? Number(headers.get("x-content-truncated"))
                : null;
            sanitizedJobImported.value = !!headers.get("x-sanitized-job-imported");
            sanitizedToolId.value = headers.get("x-sanitized-tool-id");
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
    <BAlert v-else-if="STATES.PENDING_STATES.includes(dataset.state)" show variant="warning">
        <FontAwesomeIcon :icon="faSpinner" spin />
        <span>Waiting for dataset to become available. Please check the history panel for details.</span>
    </BAlert>
    <BAlert v-else-if="dataset.state !== STATES.OK" show variant="danger">
        <FontAwesomeIcon :icon="faExclamationTriangle" />
        <span>Dataset is unavailable. Please check the history panel for details.</span>
    </BAlert>
    <div v-else class="dataset-display h-100">
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
        <TabularChunkedView v-if="contentChunked" :options="dataset" />
        <div v-else class="h-100">
            <div v-if="isBinary">
                This is a binary (or unknown to Galaxy) dataset of size {{ bytesToString(dataset.file_size) }}. Preview
                is not implemented for this filetype. Displaying as ASCII text.
            </div>
            <div v-if="contentTruncated" class="warningmessagelarge">
                <div>
                    This dataset is large and only the first {{ bytesToString(contentTruncated) }} is shown below.
                </div>
                <a :href="downloadUrl">Download</a>
            </div>
            <CenterFrame :src="previewUrl" @load="emit('load')" />
        </div>
    </div>
</template>
