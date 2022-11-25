<script setup>
import { computed, ref, onMounted, watch } from "vue";
import { BAlert, BCard, BButton, BTab, BTabs } from "bootstrap-vue";
import LoadingSpan from "components/LoadingSpan";
import ExportRecordDetails from "components/Common/ExportRecordDetails.vue";
import ExportRecordTable from "components/Common/ExportRecordTable.vue";
import ExportToFileSourceForm from "components/Common/ExportForm.vue";
import { HistoryExportService } from "./services";
import { useTaskMonitor } from "composables/taskMonitor";
import { useFileSources } from "composables/fileSources";
import { useShortTermStorage } from "composables/shortTermStorage";
import { useConfirmDialog } from "composables/confirmDialog";

const service = new HistoryExportService();

const { isRunning: isExportTaskRunning, waitForTask } = useTaskMonitor();
const { hasWritable: hasWritableFileSources } = useFileSources();
const { isPreparing: isPreparingDownload, downloadHistory, downloadObjectByRequestId } = useShortTermStorage();
const { confirm } = useConfirmDialog();

const props = defineProps({
    historyId: {
        type: String,
        required: true,
    },
});

// TODO: make this configurable by the user?
const EXPORT_PARAMS = service.defaultExportParams;

const isLoadingRecords = ref(true);
const exportRecords = ref(null);
const latestExportRecord = computed(() => (exportRecords.value?.length ? exportRecords.value.at(0) : null));
const previousExportRecords = computed(() => (exportRecords.value ? exportRecords.value.slice(1) : null));
const hasPreviousExports = computed(() => previousExportRecords.value?.length > 0);
const availableRecordsMessage = computed(() =>
    isLoadingRecords.value
        ? "Loading export records..."
        : "This history has no export records yet. You can choose one of the export options above."
);
const errorMessage = ref(null);
const actionMessage = ref(null);
const actionMessageVariant = ref(null);

onMounted(async () => {
    updateExports();
});

watch(isExportTaskRunning, (newValue, oldValue) => {
    const hasFinished = oldValue && !newValue;
    if (hasFinished) {
        updateExports();
    }
});

async function updateExports() {
    isLoadingRecords.value = true;
    try {
        errorMessage.value = null;
        exportRecords.value = await service.getExportRecords(props.historyId);
        const shouldWaitForTask = latestExportRecord.value?.isPreparing && !isExportTaskRunning.value;
        if (shouldWaitForTask) {
            waitForTask(latestExportRecord.value.taskUUID, 3000);
        }
    } catch (error) {
        errorMessage.value = error;
    }
    isLoadingRecords.value = false;
}

async function exportToFileSource(exportDirectory, fileName) {
    await service.exportToFileSource(props.historyId, exportDirectory, fileName, EXPORT_PARAMS);
    updateExports();
}

async function prepareDownload() {
    const upToDateDownloadRecord = findValidUpToDateDownloadRecord();
    if (upToDateDownloadRecord) {
        console.debug("Existing STS download found", upToDateDownloadRecord);
        downloadObjectByRequestId(upToDateDownloadRecord.stsDownloadId);
        return;
    }
    await downloadHistory(props.historyId, { pollDelayInMs: 3000, exportParams: EXPORT_PARAMS });
    updateExports();
}

function downloadFromRecord(record) {
    if (record.canDownload) {
        downloadObjectByRequestId(record.stsDownloadId);
    }
}

function findValidUpToDateDownloadRecord() {
    return exportRecords.value ? exportRecords.value.find((record) => record.canDownload && record.isUpToDate) : null;
}

async function reimportFromRecord(record) {
    const confirmed = await confirm(
        `Do you really want to import a new copy of this history exported ${record.elapsedTime}?`
    );
    if (confirmed) {
        service
            .reimportHistoryFromRecord(record)
            .then(() => {
                actionMessageVariant.value = "info";
                actionMessage.value =
                    "The history is being imported in the background. Check your histories after a while to find it.";
            })
            .catch((reason) => {
                actionMessageVariant.value = "danger";
                actionMessage.value = reason;
            });
    }
}

function onActionMessageDismissedFromRecord() {
    actionMessage.value = null;
    actionMessageVariant.value = null;
}
</script>
<template>
    <span class="history-export-component">
        <h1 class="h-lg">Export history {{ props.historyId }}</h1>

        <b-card no-body>
            <b-tabs pills card>
                <b-tab title="to direct download" title-link-class="tab-export-to-link" active>
                    <p>
                        Here you can generate a temporal download for your history. When your download link expires or
                        your history changes you can re-generate it again.
                    </p>
                    <b-button :disabled="isPreparingDownload" variant="primary" @click="prepareDownload">
                        Download
                    </b-button>
                    <span v-if="isPreparingDownload">
                        <loading-span message="Galaxy is preparing your download, this will likely take a while" />
                    </span>
                </b-tab>
                <b-tab v-if="hasWritableFileSources" title="to remote file" title-link-class="tab-export-to-file">
                    <p>
                        If you need a "more permanent" way of storing your exported history you can export it directly
                        to one of the available remote file sources here. You will be able to re-import it later as long
                        as it remains available on the remote server.
                    </p>
                    <export-to-file-source-form
                        what="history"
                        :clear-input-after-export="true"
                        @export="exportToFileSource" />
                </b-tab>
            </b-tabs>
        </b-card>

        <export-record-details
            v-if="latestExportRecord"
            :record="latestExportRecord"
            object-type="history"
            class="mt-3"
            :action-message="actionMessage"
            :action-message-variant="actionMessageVariant"
            @onDownload="downloadFromRecord"
            @onReimport="reimportFromRecord"
            @onActionMessageDismissed="onActionMessageDismissedFromRecord" />
        <b-alert v-else-if="errorMessage" variant="danger" class="mt-3" show>
            {{ errorMessage }}
        </b-alert>
        <b-alert v-else variant="info" class="mt-3" show>
            {{ availableRecordsMessage }}
        </b-alert>

        <export-record-table
            v-if="hasPreviousExports"
            :records="previousExportRecords"
            class="mt-3"
            @onDownload="downloadFromRecord"
            @onReimport="reimportFromRecord" />
    </span>
</template>
