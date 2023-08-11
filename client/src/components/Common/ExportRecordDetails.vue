<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import {
    faCheckCircle,
    faClock,
    faExclamationCircle,
    faExclamationTriangle,
    faLink,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import LoadingSpan from "components/LoadingSpan";
import { computed } from "vue";

import { GAlert, GButton, GCard, GCardTitle } from "@/component-library";

import { ExportRecordModel } from "./models/exportRecordModel";

library.add(faExclamationCircle, faExclamationTriangle, faCheckCircle, faClock, faLink);

const props = defineProps({
    record: {
        type: ExportRecordModel,
        required: true,
    },
    objectType: {
        type: String,
        required: true,
    },
    actionMessage: {
        type: String,
        default: null,
    },
    actionMessageVariant: {
        type: String,
        default: "info",
    },
});

const emit = defineEmits(["onReimport", "onDownload", "onCopyDownloadLink", "onActionMessageDismissed"]);

const title = computed(() => (props.record.isReady ? `Exported` : `Export started`));
const preparingMessage = computed(
    () => `Preparing export. This may take some time depending on the size of your ${props.objectType}`
);

async function reimportObject() {
    emit("onReimport", props.record);
}

function downloadObject() {
    emit("onDownload", props.record);
}

function copyDownloadLink() {
    emit("onCopyDownloadLink", props.record);
}

function onMessageDismissed() {
    emit("onActionMessageDismissed");
}
</script>

<template>
    <GCard class="export-record-details">
        <GCardTitle>
            <b>{{ title }}</b> {{ props.record.elapsedTime }}
        </GCardTitle>
        <p v-if="!props.record.isPreparing">
            Format: <b class="record-archive-format">{{ props.record.modelStoreFormat }}</b>
        </p>
        <span v-if="props.record.isPreparing">
            <LoadingSpan :message="preparingMessage" />
        </span>
        <div v-else>
            <div v-if="props.record.hasFailed">
                <FontAwesomeIcon
                    icon="exclamation-circle"
                    class="text-danger record-failed-icon"
                    title="Export failed" />
                <span>
                    Something failed during this export. Please try again and if the problem persist contact your
                    administrator.
                </span>
                <GAlert show variant="danger">{{ props.record.errorMessage }}</GAlert>
            </div>
            <div v-else-if="props.record.isUpToDate" title="Up to date">
                <FontAwesomeIcon icon="check-circle" class="text-success record-up-to-date-icon" />
                <span> This export record contains the latest changes of the {{ props.objectType }}. </span>
            </div>
            <div v-else>
                <FontAwesomeIcon icon="exclamation-triangle" class="text-warning record-outdated-icon" />
                <span>
                    This export is outdated and contains the changes of this {{ props.objectType }} from
                    {{ props.record.elapsedTime }}.
                </span>
            </div>

            <p v-if="props.record.canExpire" class="mt-3">
                <span v-if="props.record.hasExpired">
                    <FontAwesomeIcon icon="clock" class="text-danger record-expired-icon" /> This download link has
                    expired.
                </span>
                <span v-else>
                    <FontAwesomeIcon icon="clock" class="text-warning record-expiration-warning-icon" /> This download
                    link expires {{ props.record.expirationElapsedTime }}.
                </span>
            </p>

            <div v-if="props.record.isReady">
                <p class="mt-3">You can do the following actions with this {{ props.objectType }} export:</p>
                <GAlert
                    v-if="props.actionMessage !== null"
                    :variant="props.actionMessageVariant"
                    show
                    fade
                    dismissible
                    @dismissed="onMessageDismissed">
                    {{ props.actionMessage }}
                </GAlert>
                <div v-else class="actions">
                    <GButton
                        v-if="props.record.canDownload"
                        class="record-download-btn"
                        variant="primary"
                        @click="downloadObject">
                        Download
                    </GButton>
                    <GButton
                        v-if="props.record.canDownload"
                        title="Copy Download Link"
                        size="sm"
                        variant="link"
                        @click.stop="copyDownloadLink">
                        <FontAwesomeIcon icon="link" />
                    </GButton>
                    <GButton
                        v-if="props.record.canReimport"
                        class="record-reimport-btn"
                        variant="primary"
                        @click="reimportObject">
                        Reimport
                    </GButton>
                </div>
            </div>
        </div>
    </GCard>
</template>
