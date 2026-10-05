<script setup lang="ts">
/*
    A Galaxy Button with logic for interfacing with Galaxy's short term storage
    component (STS).
*/
import { faDownload, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios, { type AxiosResponse } from "axios";
import { computed, onBeforeUnmount, ref } from "vue";

import type { ComponentColor, ComponentSize } from "@/components/BaseComponents/componentVariants";
import { useConfig } from "@/composables/config";
import { Toast } from "@/composables/toast";
import { getAppRoot } from "@/onload/loadConfig";
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

const { config, isConfigLoaded } = useConfig(true);

const waiting = ref(false);

let timeout: ReturnType<typeof setTimeout> | undefined;

const canDownload = computed(() => {
    if (!config.value.enable_celery_tasks) {
        return props.fallbackUrl != null;
    }
    return true;
});

function onDownload() {
    if (!config.value.enable_celery_tasks) {
        window.open(withPrefix(props.fallbackUrl ?? ""));
    } else {
        waiting.value = true;
        axios.post(props.downloadEndpoint, props.postParameters).then(handleInitialize).catch(handleError);
    }
}

function handleInitialize(response: AxiosResponse) {
    const storageRequestId = response.data.storage_request_id;
    pollStorageRequestId(storageRequestId);
}

function pollStorageRequestId(storageRequestId: string) {
    const url = `${getAppRoot()}api/short_term_storage/${storageRequestId}/ready`;
    axios
        .get(url)
        .then((r) => {
            handlePollResponse(r, storageRequestId);
        })
        .catch(handleError);
}

function handlePollResponse(response: AxiosResponse, storageRequestId: string) {
    const ready = response.data;
    if (ready) {
        const url = `${getAppRoot()}api/short_term_storage/${storageRequestId}`;
        window.location.assign(url);
        waiting.value = false;
    } else {
        pollAfterDelay(storageRequestId);
    }
}

function handleError(err: unknown) {
    Toast.error(`Failed to generate download: ${err}`);
    waiting.value = false;
}

function clearPollTimeout() {
    if (timeout) {
        clearTimeout(timeout);
    }
}

function pollAfterDelay(storageRequestId: string) {
    clearPollTimeout();
    timeout = setTimeout(() => {
        pollStorageRequestId(storageRequestId);
    }, POLL_DELAY);
}

onBeforeUnmount(() => {
    clearPollTimeout();
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
