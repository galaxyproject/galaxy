<script setup>
import { computed, ref, reactive, onMounted, watch } from "vue";
import { BAlert, BCard, BButton, BTab, BTabs } from "bootstrap-vue";
import LoadingSpan from "components/LoadingSpan";
import ExportRecordDetails from "components/Common/ExportRecordDetails.vue";
import ExportRecordTable from "components/Common/ExportRecordTable.vue";
import ExportOptions from "./ExportOptions.vue";
import ExportToFileSourceForm from "components/Common/ExportForm.vue";
import { getExportRecords, exportToFileSource, reimportHistoryFromRecord } from "./services";
import { useTaskMonitor } from "composables/taskMonitor";
import { useFileSources } from "composables/fileSources";
import { useShortTermStorage, DEFAULT_EXPORT_PARAMS } from "composables/shortTermStorage";
import { useConfirmDialog } from "composables/confirmDialog";

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

const exportParams = reactive(DEFAULT_EXPORT_PARAMS);
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
        exportRecords.value = await getExportRecords(props.historyId);
        const shouldWaitForTask = latestExportRecord.value?.isPreparing && !isExportTaskRunning.value;
        if (shouldWaitForTask) {
            waitForTask(latestExportRecord.value.taskUUID, 3000);
        }
    } catch (error) {
        errorMessage.value = error;
    }
    isLoadingRecords.value = false;
}

async function doExportToFileSource(exportDirectory, fileName) {
    await exportToFileSource(props.historyId, exportDirectory, fileName, exportParams);
    updateExports();
}

async function prepareDownload() {
    const upToDateDownloadRecord = findValidUpToDateDownloadRecord();
    if (upToDateDownloadRecord) {
        downloadObjectByRequestId(upToDateDownloadRecord.stsDownloadId);
        return;
    }
    await downloadHistory(props.historyId, { pollDelayInMs: 3000, exportParams: exportParams });
    updateExports();
}

function downloadFromRecord(record) {
    if (record.canDownload) {
        downloadObjectByRequestId(record.stsDownloadId);
    }
}

function findValidUpToDateDownloadRecord() {
    return exportRecords.value
        ? exportRecords.value.find(
              (record) => record.canDownload && record.isUpToDate && record.exportParams?.equals(exportParams)
          )
        : null;
}

async function reimportFromRecord(record) {
    const confirmed = await confirm(
        `Do you really want to import a new copy of this history exported ${record.elapsedTime}?`
    );
    if (confirmed) {
        reimportHistoryFromRecord(record)
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

function updateExportParams(newParams) {
    exportParams.modelStoreFormat = newParams.modelStoreFormat;
    exportParams.includeFiles = newParams.includeFiles;
    exportParams.includeDeleted = newParams.includeDeleted;
    exportParams.includeHidden = newParams.includeHidden;
}
</script>
<template>
    <span class="history-export-component">
        <h1 class="h-lg">Export history {{ props.historyId }}</h1>

        <export-options
            id="history-export-options"
            :export-params="exportParams"
            @onValueChanged="updateExportParams" />

        <b-card no-body class="mt-3">
            <b-tabs pills card>
                <b-tab id="direct-download-tab" title="to direct download" title-link-class="tab-export-to-link" active>
                    <p>
                        Here you can generate a temporal download for your history. When your download link expires or
                        your history changes you can re-generate it again.
                    </p>
                    <b-alert show variant="warning">
                        History archive downloads can expire and are removed at regular intervals. For permanent
                        storage, export to a <b>remote file</b> or download and then import the archive on another
                        Galaxy server.
                    </b-alert>
                    <b-button
                        class="direct-download-btn"
                        :disabled="isPreparingDownload"
                        variant="primary"
                        @click="prepareDownload">
                        Download
                    </b-button>
                    <span v-if="isPreparingDownload">
                        <loading-span message="Galaxy is preparing your download, this will likely take a while" />
                    </span>
                </b-tab>
                <b-tab
                    v-if="hasWritableFileSources"
                    id="file-source-tab"
                    title="to remote file"
                    title-link-class="tab-export-to-file">
                    <p>
                        If you need a "more permanent" way of storing your history archive you can export it directly to
                        one of the available remote file sources here. You will be able to re-import it later as long as
                        it remains available on the remote server.
                    </p>
                    <export-to-file-source-form
                        what="history"
                        :clear-input-after-export="true"
                        @export="doExportToFileSource" />
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
        <b-alert v-else-if="errorMessage" id="last-export-record-error-alert" variant="danger" class="mt-3" show>
            {{ errorMessage }}
        </b-alert>
        <b-alert v-else id="no-export-records-alert" variant="info" class="mt-3" show>
            {{ availableRecordsMessage }}
        </b-alert>

        <export-record-table
            v-if="hasPreviousExports"
            id="previous-export-records"
            :records="previousExportRecords"
            class="mt-3"
            @onDownload="downloadFromRecord"
            @onReimport="reimportFromRecord" />
    </span>
</template>
