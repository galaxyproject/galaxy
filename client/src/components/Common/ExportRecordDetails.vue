<script setup>
import { computed } from "vue";
import { BCard, BCardTitle } from "bootstrap-vue";
import LoadingSpan from "components/LoadingSpan";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExclamationCircle, faExclamationTriangle, faCheckCircle, faClock } from "@fortawesome/free-solid-svg-icons";
import { ExportRecordModel } from "./models/exportRecordModel";

library.add(faExclamationCircle, faExclamationTriangle, faCheckCircle, faClock);

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

const emit = defineEmits(["onReimport", "onDownload", "onActionMessageDismissed"]);

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

function onMessageDismissed() {
    emit("onActionMessageDismissed");
}
</script>

<template>
    <b-card>
        <b-card-title>
            <b>{{ title }}</b> {{ props.record.elapsedTime }}
        </b-card-title>
        <span v-if="props.record.isPreparing">
            <loading-span :message="preparingMessage" />
        </span>
        <div v-else>
            <div v-if="props.record.hasFailed">
                <font-awesome-icon icon="exclamation-circle" class="text-danger" title="Export failed" />
                <span>
                    Something failed during this export. Please try again and if the problem persist contact your
                    administrator.
                </span>
            </div>
            <div v-else-if="props.record.isUpToDate" title="Up to date">
                <font-awesome-icon icon="check-circle" class="text-success" />
                <span> This export record contains the latest changes of the {{ props.objectType }}. </span>
            </div>
            <div v-else>
                <font-awesome-icon icon="exclamation-triangle" class="text-warning" />
                <span>
                    This export is outdated and contains the changes of this {{ props.objectType }} from
                    {{ props.record.elapsedTime }}.
                </span>
            </div>

            <p v-if="props.record.canExpire" class="mt-3">
                <span v-if="props.record.hasExpired">
                    <font-awesome-icon icon="clock" class="text-danger" /> This download link has expired.
                </span>
                <span v-else>
                    <font-awesome-icon icon="clock" class="text-warning" /> This download link expires
                    {{ props.record.expirationElapsedTime }}.
                </span>
            </p>

            <div v-if="props.record.isReady">
                <p class="mt-3">You can do the following actions with this {{ props.objectType }} export:</p>
                <b-alert
                    v-if="props.actionMessage !== null"
                    :variant="props.actionMessageVariant"
                    show
                    fade
                    dismissible
                    @dismissed="onMessageDismissed">
                    {{ props.actionMessage }}
                </b-alert>
                <div v-else class="actions">
                    <b-button v-if="props.record.canDownload" variant="primary" @click="downloadObject">
                        Download
                    </b-button>
                    <b-button v-if="props.record.canReimport" variant="primary" @click="reimportObject">
                        Reimport
                    </b-button>
                </div>
            </div>
        </div>
    </b-card>
</template>
