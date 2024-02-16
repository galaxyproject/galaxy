<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faFileExport } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BCard, BTab, BTabs } from "bootstrap-vue";
import LoadingSpan from "components/LoadingSpan";
import { useConfirmDialog } from "composables/confirmDialog";
import { useFileSources } from "composables/fileSources";
import { DEFAULT_EXPORT_PARAMS, useShortTermStorage } from "composables/shortTermStorage";
import { useTaskMonitor } from "composables/taskMonitor";
import { copy as sendToClipboard } from "utils/clipboard";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { RouterLink } from "vue-router";

import {
    exportHistoryToFileSource,
    fetchHistoryExportRecords,
    reimportHistoryFromRecord,
} from "@/api/histories.export";
import { useHistoryStore } from "@/stores/historyStore";
import { absPath } from "@/utils/redirect";

import ExportOptions from "./ExportOptions.vue";
import ExportToFileSourceForm from "@/components/Common/ExportForm.vue";
import ExportToRDMRepositoryForm from "@/components/Common/ExportRDMForm.vue";
import ExportRecordDetails from "@/components/Common/ExportRecordDetails.vue";
import ExportRecordTable from "@/components/Common/ExportRecordTable.vue";

const {
    isRunning: isExportTaskRunning,
    waitForTask,
    requestHasFailed: taskMonitorRequestFailed,
    hasFailed: taskHasFailed,
} = useTaskMonitor();

const { hasWritable: hasWritableFileSources } = useFileSources({ exclude: ["rdm"] });
const { hasWritable: hasWritableRDMFileSources } = useFileSources({ include: ["rdm"] });

const {
    isPreparing: isPreparingDownload,
    prepareHistoryDownload,
    downloadObjectByRequestId,
    getDownloadObjectUrl,
} = useShortTermStorage();

const { confirm } = useConfirmDialog();

const props = defineProps({
    historyId: {
        type: String,
        required: true,
    },
});

library.add(faFileExport);

const POLLING_DELAY = 3000;

const exportParams = reactive(DEFAULT_EXPORT_PARAMS);
const isLoadingRecords = ref(true);
const exportRecords = ref(null);

const historyName = computed(() => history.value?.name ?? props.historyId);
const latestExportRecord = computed(() => (exportRecords.value?.length ? exportRecords.value.at(0) : null));
const isLatestExportRecordReadyToDownload = computed(
    () =>
        latestExportRecord.value &&
        latestExportRecord.value.isUpToDate &&
        latestExportRecord.value.canDownload &&
        latestExportRecord.value.exportParams?.equals(exportParams)
);
const canGenerateDownload = computed(() => !isPreparingDownload.value && !isLatestExportRecordReadyToDownload.value);
const previousExportRecords = computed(() => (exportRecords.value ? exportRecords.value.slice(1) : null));
const hasPreviousExports = computed(() => previousExportRecords.value?.length > 0);
const availableRecordsMessage = computed(() =>
    isLoadingRecords.value
        ? "Loading export records..."
        : "This history has no export records yet. You can choose one of the export options above."
);

const historyStore = useHistoryStore();

const history = computed(() => {
    const history = historyStore.getHistoryById(props.historyId);
    return history;
});

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
        exportRecords.value = await fetchHistoryExportRecords(props.historyId);
        const shouldWaitForTask =
            latestExportRecord.value?.isPreparing &&
            !isExportTaskRunning.value &&
            !taskMonitorRequestFailed.value &&
            !taskHasFailed.value;
        if (shouldWaitForTask) {
            waitForTask(latestExportRecord.value.taskUUID, POLLING_DELAY);
        }
        if (taskMonitorRequestFailed.value) {
            errorMessage.value = "Something went wrong trying to get the export progress. Please check back later.";
        }
        if (taskHasFailed.value) {
            errorMessage.value = "Something went wrong trying to export the history. Please try again later.";
        }
    } catch (error) {
        errorMessage.value = error;
    } finally {
        isLoadingRecords.value = false;
    }
}

async function doExportToFileSource(exportDirectory, fileName) {
    await exportHistoryToFileSource(props.historyId, exportDirectory, fileName, exportParams);
    updateExports();
}

async function prepareDownload() {
    await prepareHistoryDownload(props.historyId, { pollDelayInMs: POLLING_DELAY, exportParams: exportParams });
    updateExports();
}

function downloadFromRecord(record) {
    if (record.canDownload) {
        downloadObjectByRequestId(record.stsDownloadId);
    }
}

function copyDownloadLinkFromRecord(record) {
    if (record.canDownload) {
        const relativeLink = getDownloadObjectUrl(record.stsDownloadId);
        sendToClipboard(absPath(relativeLink), "Download link copied to your clipboard");
    }
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
        <FontAwesomeIcon icon="file-export" size="2x" class="text-primary float-left mr-2" />
        <h1 class="h-lg">
            Export
            <LoadingSpan v-if="!history" spinner-only />
            <b v-else id="history-name">{{ historyName }}</b>
        </h1>

        <ExportOptions
            id="history-export-options"
            class="mt-3"
            :export-params="exportParams"
            @onValueChanged="updateExportParams" />

        <h2 class="h-md mt-3">How do you want to export this history?</h2>
        <BCard no-body class="mt-3">
            <BTabs pills card vertical>
                <BTab id="direct-download-tab" title="to direct download" title-link-class="tab-export-to-link" active>
                    <p>
                        Here you can generate a temporal download for your history. When your download link expires or
                        your history changes you can re-generate it again.
                    </p>
                    <BAlert show variant="warning">
                        History archive downloads can expire and are removed at regular intervals. For permanent
                        storage, export to a <b>remote file</b> or download and then import the archive on another
                        Galaxy server.
                    </BAlert>
                    <BButton
                        class="gen-direct-download-btn"
                        :disabled="!canGenerateDownload"
                        variant="primary"
                        @click="prepareDownload">
                        Generate direct download
                    </BButton>
                    <span v-if="isPreparingDownload">
                        <LoadingSpan message="Galaxy is preparing your download, this will likely take a while" />
                    </span>
                    <BAlert v-else-if="isLatestExportRecordReadyToDownload" variant="success" class="mt-3" show>
                        The latest export record is ready. Use the download button below to download it or change the
                        advanced export options above to generate a new one.
                    </BAlert>
                </BTab>
                <BTab
                    v-if="hasWritableFileSources"
                    id="file-source-tab"
                    title="to remote file"
                    title-link-class="tab-export-to-file">
                    <p>
                        If you need a "more permanent" way of storing your history archive you can export it directly to
                        one of the available remote file sources here. You will be able to re-import it later as long as
                        it remains available on the remote server.
                    </p>
                    <ExportToFileSourceForm
                        what="history"
                        :clear-input-after-export="true"
                        @export="doExportToFileSource" />
                </BTab>
                <BTab
                    v-if="hasWritableRDMFileSources"
                    id="rdm-file-source-tab"
                    title="to RDM repository"
                    title-link-class="tab-export-to-rdm-repo">
                    <p>You can <b>upload your history</b> to one of the available RDM repositories here.</p>
                    <p>
                        Your history export archive needs to be uploaded to an existing <i>draft</i> record. You will
                        need to create a <b>new record</b> on the repository or select an existing
                        <b>draft record</b> and then export your history to it.
                    </p>
                    <BAlert show variant="info">
                        You may need to setup your credentials for the selected repository in your
                        <RouterLink to="/user/information" target="_blank">settings page</RouterLink> to be able to
                        export. You can also define some default options for the export in those settings, like the
                        public name you want to associate with your records or whether you want to publish them
                        immediately or keep them as drafts after export.
                    </BAlert>
                    <ExportToRDMRepositoryForm
                        what="history"
                        :default-filename="historyName + ' (Galaxy History)'"
                        :default-record-name="historyName"
                        :clear-input-after-export="true"
                        @export="doExportToFileSource" />
                </BTab>
            </BTabs>
        </BCard>

        <BAlert v-if="errorMessage" id="last-export-record-error-alert" variant="danger" class="mt-3" show>
            {{ errorMessage }}
        </BAlert>
        <div v-else-if="latestExportRecord">
            <h2 class="h-md mt-3">Latest Export Record</h2>
            <ExportRecordDetails
                :record="latestExportRecord"
                object-type="history"
                class="mt-3"
                :action-message="actionMessage"
                :action-message-variant="actionMessageVariant"
                @onDownload="downloadFromRecord"
                @onCopyDownloadLink="copyDownloadLinkFromRecord"
                @onReimport="reimportFromRecord"
                @onActionMessageDismissed="onActionMessageDismissedFromRecord" />
        </div>
        <BAlert v-else id="no-export-records-alert" variant="info" class="mt-3" show>
            {{ availableRecordsMessage }}
        </BAlert>

        <ExportRecordTable
            v-if="hasPreviousExports"
            id="previous-export-records"
            :records="previousExportRecords"
            class="mt-3"
            @onDownload="downloadFromRecord"
            @onReimport="reimportFromRecord" />
    </span>
</template>
