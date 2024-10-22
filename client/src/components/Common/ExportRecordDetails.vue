<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import {
    faCheckCircle,
    faClock,
    faExclamationCircle,
    faExclamationTriangle,
    faLink,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { computed } from "vue";

import type { ColorVariant } from ".";
import { type ExportRecord } from "./models/exportRecordModel";

import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faCheckCircle, faClock, faExclamationCircle, faExclamationTriangle, faLink);

interface Props {
    record: ExportRecord;
    objectType: string;
    actionMessage?: string;
    actionMessageVariant?: ColorVariant;
}

const props = withDefaults(defineProps<Props>(), {
    actionMessage: undefined,
    actionMessageVariant: "info",
});

const emit = defineEmits<{
    (e: "onActionMessageDismissed"): void;
    (e: "onReimport", record: ExportRecord): void;
    (e: "onDownload", record: ExportRecord): void;
    (e: "onCopyDownloadLink", record: ExportRecord): void;
}>();

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
    <div class="export-record-details">
        <Heading size="sm">
            <b>{{ title }}</b> {{ props.record.elapsedTime }}
        </Heading>

        <p v-if="!props.record.isPreparing">
            Format: <b class="record-archive-format">{{ props.record.modelStoreFormat }}</b>
        </p>

        <span v-if="props.record.isPreparing">
            <LoadingSpan :message="preparingMessage" />
        </span>
        <div v-else>
            <div v-if="props.record.hasFailed">
                <FontAwesomeIcon
                    :icon="faExclamationCircle"
                    class="text-danger record-failed-icon"
                    title="Export failed" />

                <span>
                    Something failed during this export. Please try again and if the problem persist contact your
                    administrator.
                </span>

                <BAlert show variant="danger">{{ props.record.errorMessage }}</BAlert>
            </div>
            <div v-else-if="props.record.isUpToDate" title="Up to date">
                <FontAwesomeIcon :icon="faCheckCircle" class="text-success record-up-to-date-icon" />
                <span> This export record contains the latest changes of the {{ props.objectType }}. </span>
            </div>
            <div v-else>
                <FontAwesomeIcon :icon="faExclamationTriangle" class="text-warning record-outdated-icon" />
                <span>
                    This export is outdated and contains the changes of this {{ props.objectType }} from
                    {{ props.record.elapsedTime }}.
                </span>
            </div>

            <p v-if="props.record.canExpire" class="mt-3">
                <span v-if="props.record.hasExpired">
                    <FontAwesomeIcon :icon="faClock" class="text-danger record-expired-icon" />
                    This download link has expired.
                </span>
                <span v-else>
                    <FontAwesomeIcon :icon="faClock" class="text-warning record-expiration-warning-icon" />
                    This download link expires {{ props.record.expirationElapsedTime }}.
                </span>
            </p>

            <div v-if="props.record.isReady">
                <p class="mt-3">You can do the following actions with this {{ props.objectType }} export:</p>

                <BAlert
                    v-if="props.actionMessage !== undefined"
                    :variant="props.actionMessageVariant"
                    show
                    fade
                    dismissible
                    @dismissed="onMessageDismissed">
                    {{ props.actionMessage }}
                </BAlert>
                <div v-else class="actions">
                    <BButton
                        v-if="props.record.canDownload"
                        class="record-download-btn"
                        variant="primary"
                        @click="downloadObject">
                        Download
                    </BButton>

                    <BButton
                        v-if="props.record.canDownload"
                        title="Copy Download Link"
                        size="sm"
                        variant="link"
                        @click.stop="copyDownloadLink">
                        <FontAwesomeIcon :icon="faLink" />
                    </BButton>

                    <BButton
                        v-if="props.record.canReimport"
                        class="record-reimport-btn"
                        variant="primary"
                        @click="reimportObject">
                        Reimport
                    </BButton>
                </div>
            </div>
        </div>
    </div>
</template>
