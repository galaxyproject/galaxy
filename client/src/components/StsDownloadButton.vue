<script setup lang="ts">
/*
    A Galaxy Button with logic for interfacing with Galaxy's short term storage
    component (STS).
*/
import { faDownload, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import { computed, ref, watch } from "vue";

import type { ComponentColor, ComponentSize } from "@/components/BaseComponents/componentVariants";
import { useConfig } from "@/composables/config";
import { useShortTermStorage } from "@/composables/shortTermStorage";
import { useShortTermStorageMonitor } from "@/composables/shortTermStorageMonitor";
import { Toast } from "@/composables/toast";
import { withPrefix } from "@/utils/redirect";

import GButton from "@/components/BaseComponents/GButton.vue";

const POLL_DELAY = 200;

interface Props {
    /** Endpoint that starts preparing the download */
    downloadEndpoint: string;
    /** Tooltip text */
    title: string;
    /**
     * Button color
     * @default undefined
     */
    color?: ComponentColor;
    /**
     * Direct download URL, used when Celery tasks are disabled
     * @default null
     */
    fallbackUrl?: string | null;
    /**
     * Outline variant of the button
     * @default false
     */
    outline?: boolean;
    /**
     * Payload posted to the download endpoint
     * @default {}
     */
    postParameters?: Record<string, unknown>;
    /**
     * Button size
     * @default "medium"
     */
    size?: ComponentSize;
}

const props = withDefaults(defineProps<Props>(), {
    color: undefined,
    fallbackUrl: null,
    outline: false,
    postParameters: () => ({}),
    size: "medium",
});

const { config, isConfigLoaded } = useConfig();

const waiting = ref(false);
const storageRequestId = ref<string>();

const { waitForTask, isCompleted, hasFailed, taskStatus } = useShortTermStorageMonitor();
const { downloadObjectByRequestId } = useShortTermStorage();

const canDownload = computed(() => {
    if (!config.value.enable_celery_tasks) {
        return props.fallbackUrl != null;
    }
    return true;
});

async function onDownload() {
    if (!config.value.enable_celery_tasks) {
        window.open(withPrefix(props.fallbackUrl ?? ""));
        return;
    }
    waiting.value = true;
    try {
        const response = await axios.post(props.downloadEndpoint, props.postParameters);
        const requestId: string = response.data.storage_request_id;
        storageRequestId.value = requestId;
        waitForTask(requestId, POLL_DELAY);
    } catch (err) {
        handleError(err);
    }
}

function handleError(err: unknown) {
    Toast.error(`Failed to generate download: ${err}`);
    waiting.value = false;
}

watch(isCompleted, (completed) => {
    if (completed && storageRequestId.value) {
        downloadObjectByRequestId(storageRequestId.value);
        waiting.value = false;
    }
});

watch(hasFailed, (failed) => {
    if (failed) {
        handleError(taskStatus.value);
    }
});
</script>

<template>
    <GButton
        v-if="isConfigLoaded && canDownload"
        tooltip
        tooltip-placement="bottom"
        :title="title"
        :color="color"
        :outline="outline"
        :size="size"
        @click="onDownload()">
        Generate
        <FontAwesomeIcon v-if="waiting" :icon="faSpinner" spin />
        <FontAwesomeIcon v-else :icon="faDownload" />
    </GButton>
</template>
