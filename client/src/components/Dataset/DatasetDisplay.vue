<script setup lang="ts">
import { faExclamationTriangle, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useDatasetStore } from "@/stores/datasetStore";
import { useDatatypeStore } from "@/stores/datatypeStore";
import { useUserStore } from "@/stores/userStore";
import STATES from "@/utils/datasetStates";
import { absPath, withPrefix } from "@/utils/redirect";
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
const datatypeStore = useDatatypeStore();

const emit = defineEmits(["load"]);

const props = defineProps<Props>();

const contentTruncated = ref<number | null>(null);
const contentChunked = ref<boolean>(false);
const errorMessage = ref<string>("");
const previewLoaded = ref<boolean>(false);
const previewFrameUrl = ref<string | null>(null);
const sanitizedJobImported = ref<boolean>(false);
const sanitizedToolId = ref<string | null>(null);

const { isAdmin } = storeToRefs(useUserStore());

const dataset = computed(() => getDataset(props.datasetId));
const datasetUrl = computed(() => `/datasets/${props.datasetId}/display/`);
const downloadUrl = computed(() =>
    withPrefix(`/api/datasets/${props.datasetId}/download?to_ext=${dataset.value?.file_ext}`),
);
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
    async (_, __, onCleanup) => {
        previewLoaded.value = false;
        contentChunked.value = false;
        contentTruncated.value = null;
        sanitizedJobImported.value = false;
        sanitizedToolId.value = null;
        errorMessage.value = "";
        const existingFrameUrl = previewFrameUrl.value;
        previewFrameUrl.value = null;

        const controller = new AbortController();
        if (existingFrameUrl?.startsWith("blob:")) {
            URL.revokeObjectURL(existingFrameUrl);
        }
        onCleanup(() => {
            controller.abort();
            if (previewFrameUrl.value?.startsWith("blob:")) {
                URL.revokeObjectURL(previewFrameUrl.value);
            }
            previewFrameUrl.value = null;
        });

        try {
            const extension = dataset.value?.file_ext;
            const datatypeDetails = extension ? await datatypeStore.fetchDatatypeDetails(extension) : null;
            // HTML-like and composite previews need a real /display/ URL so relative assets keep working.
            const useDirectPreview = Boolean(extension?.endsWith("html") || datatypeDetails?.composite_files?.length);
            const method = useDirectPreview ? "HEAD" : "GET";
            const response = await fetch(absPath(previewUrl.value), { method, signal: controller.signal });
            const { headers } = response;
            contentChunked.value = !!headers.get("x-content-chunked");
            contentTruncated.value = headers.get("x-content-truncated")
                ? Number(headers.get("x-content-truncated"))
                : null;
            sanitizedJobImported.value = !!headers.get("x-sanitized-job-imported");
            sanitizedToolId.value = headers.get("x-sanitized-tool-id");
            if (!response.ok) {
                throw new Error(`${response.status} ${response.statusText}`);
            }
            if (useDirectPreview) {
                // Iframe request delayed until after this fetch completes so the duplicate download is sequential
                // (which helps to make use of the objectstore cache for the second request).
                previewFrameUrl.value = previewUrl.value;
            } else if (!contentChunked.value) {
                const blob = await response.blob();
                previewFrameUrl.value = URL.createObjectURL(blob);
            }
        } catch (e) {
            if (!controller.signal.aborted) {
                errorMessage.value = errorMessageAsString(e);
                console.error(e);
            }
        }
        if (!controller.signal.aborted) {
            previewLoaded.value = true;
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
    <BAlert v-else-if="!STATES.OK_STATES.includes(dataset.state)" show variant="danger">
        <FontAwesomeIcon :icon="faExclamationTriangle" />
        <span>Dataset is unavailable. Please check the history panel for details.</span>
    </BAlert>
    <LoadingSpan v-else-if="!previewLoaded" message="Loading dataset content" />
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
            <CenterFrame v-if="previewFrameUrl" :src="previewFrameUrl" @load="emit('load')" />
        </div>
    </div>
</template>
