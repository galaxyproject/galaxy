<template>
    <GButton
        v-if="isConfigLoaded && canDownload(config)"
        tooltip
        tooltip-placement="bottom"
        :title="title"
        :color="color"
        :outline="outline"
        :size="size"
        @click="onDownload(config)">
        Generate
        <FontAwesomeIcon v-if="waiting" icon="spinner" spin />
        <FontAwesomeIcon v-else icon="download" />
    </GButton>
</template>

<script>
/*
    A Galaxy Button with logic for interfacing with Galaxy's short term storage
    component (STS).
*/
import { library } from "@fortawesome/fontawesome-svg-core";
import { faDownload, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import { Toast } from "composables/toast";
import { getAppRoot } from "onload/loadConfig";
import { withPrefix } from "utils/redirect";

import { useConfig } from "@/composables/config";

import GButton from "./BaseComponents/GButton.vue";

library.add(faDownload, faSpinner);
export default {
    components: {
        FontAwesomeIcon,
        GButton,
    },
    props: {
        title: {
            type: String,
            required: true,
        },
        downloadEndpoint: {
            type: String,
            required: true,
        },
        postParameters: {
            type: Object,
            default: () => {
                return {};
            },
        },
        fallbackUrl: {
            type: String,
            default: null,
        },
        color: {
            type: String,
            default: null,
        },
        outline: {
            type: Boolean,
            default: false,
        },
        size: {
            type: String,
            default: "medium",
        },
    },
    setup() {
        const { config, isConfigLoaded } = useConfig(true);
        return { config, isConfigLoaded };
    },
    data() {
        return {
            waiting: false,
            delay: 200,
        };
    },
    destroyed() {
        this.clearTimeout();
    },
    methods: {
        canDownload(config) {
            if (!config.enable_celery_tasks) {
                return this.fallbackUrl != null;
            }
            return true;
        },
        onDownload(config) {
            if (!config.enable_celery_tasks) {
                window.open(withPrefix(this.fallbackUrl));
            } else {
                this.waiting = true;
                axios
                    .post(this.downloadEndpoint, this.postParameters)
                    .then(this.handleInitialize)
                    .catch(this.handleError);
            }
        },
        handleInitialize(response) {
            const storageRequestId = response.data.storage_request_id;
            this.pollStorageRequestId(storageRequestId);
        },
        pollStorageRequestId(storageRequestId) {
            const url = `${getAppRoot()}api/short_term_storage/${storageRequestId}/ready`;
            axios
                .get(url)
                .then((r) => {
                    this.handlePollResponse(r, storageRequestId);
                })
                .catch(this.handleError);
        },
        handlePollResponse(response, storageRequestId) {
            const ready = response.data;
            if (ready) {
                const url = `${getAppRoot()}api/short_term_storage/${storageRequestId}`;
                window.location.assign(url);
                this.waiting = false;
            } else {
                this.pollAfterDelay(storageRequestId);
            }
        },
        handleError(err) {
            Toast.error(`Failed to generate download: ${err}`);
            this.waiting = false;
        },
        clearTimeout() {
            if (this.timeout) {
                clearTimeout(this.timeout);
            }
        },
        pollAfterDelay(storageRequestId) {
            this.clearTimeout();
            this.timeout = setTimeout(() => {
                this.pollStorageRequestId(storageRequestId);
            }, this.delay);
        },
    },
};
</script>
