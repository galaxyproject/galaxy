<script setup>
import { computed } from "vue";
import { BCard, BCardTitle } from "bootstrap-vue";
import UtcDate from "components/UtcDate";
import LoadingSpan from "components/LoadingSpan";
import { formatDistanceToNow, parseISO } from "date-fns";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ExportRecordModel } from "./models/exportRecordModel";

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
const elapsedTime = computed(() => formatDistanceToNow(parseISO(`${props.record.date}Z`), { addSuffix: true }));
const statusMessage = computed(() => {
    if (props.record.hasFailed) {
        return `Something failed during this export. Please try again and if the problem persist contact your administrator.`;
    }
    if (props.record.isUpToDate) {
        return `This export contains the latest changes of the ${props.objectType}.`;
    }
    return `This export is outdated and contains the changes of this ${props.objectType} from ${elapsedTime.value}.`;
});
const readyMessage = computed(() => `You can do the following actions with this ${props.objectType} export:`);
const preparingMessage = computed(
    () => `Preparing export. This may take some time depending on the size of your ${props.objectType}`
);

function reimportObject() {
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
            <b>{{ title }}</b> <UtcDate :date="props.record.date" mode="elapsed" />
        </b-card-title>
        <span v-if="props.record.isPreparing">
            <loading-span :message="preparingMessage" />
        </span>
        <div v-else>
            <font-awesome-icon v-if="props.record.isUpToDate" icon="check-circle" class="text-success" />
            <font-awesome-icon v-else-if="props.record.hasFailed" icon="exclamation-circle" class="text-danger" />
            <font-awesome-icon v-else icon="exclamation-triangle" class="text-warning" />
            <span>
                {{ statusMessage }}
            </span>
            <div v-if="props.record.isReady">
                <p class="mt-3">
                    {{ readyMessage }}
                </p>
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
