<template>
    <config-provider v-slot="{ config, loading }">
        <b-button
            v-if="!loading && canDownload(config)"
            v-b-tooltip.hover.bottom
            :title="title"
            :variant="variant"
            role="button"
            @click="onDownload(config)">
            <font-awesome-icon v-if="waiting" icon="spinner" spin />
            <font-awesome-icon v-else icon="download" />
        </b-button>
    </config-provider>
</template>

<script>
/*
    A Bootstrap Button with logic for interfacing with Galaxy's short term storage
    component (STS).
*/
import { getAppRoot } from "onload/loadConfig";
import { BButton } from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faDownload, faSpinner } from "@fortawesome/free-solid-svg-icons";
library.add(faDownload, faSpinner);
import ConfigProvider from "components/providers/ConfigProvider";
import { Toast } from "composables/toast";
import axios from "axios";
import { withPrefix } from "utils/redirect";
export default {
    components: {
        ConfigProvider,
        FontAwesomeIcon,
        BButton,
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
        variant: {
            type: String,
            default: null,
        },
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
                window.location.assign(withPrefix(this.fallbackUrl));
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
