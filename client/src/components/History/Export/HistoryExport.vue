<script setup lang="ts">
import { faFileExport, faList } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

import type { AnyHistory } from "@/api";
import {
    exportHistoryToFileSource,
    fetchHistoryExportRecords,
    reimportHistoryFromRecord,
} from "@/api/histories.export";
import type { ColorVariant } from "@/components/Common";
import type { ExportParams, ExportRecord } from "@/components/Common/models/exportRecordModel";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useDownloadTracker } from "@/composables/downloadTracker";
import { useShortTermStorage } from "@/composables/shortTermStorage";
import { useTaskMonitor } from "@/composables/taskMonitor";
import { useHistoryStore } from "@/stores/historyStore";
import { copy as sendToClipboard } from "@/utils/clipboard";
import { absPath } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import type { HistoryExportData } from "./types";

import HistoryExportWizard from "./HistoryExportWizard.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import ExportRecordDetails from "@/components/Common/ExportRecordDetails.vue";
import ExportRecordTable from "@/components/Common/ExportRecordTable.vue";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const {
    isRunning: isExportTaskRunning,
    waitForTask,
    stopWaitingForTask,
    requestHasFailed: taskMonitorRequestFailed,
    hasFailed: taskHasFailed,
} = useTaskMonitor();

const {
    isPreparing: isPreparingDownload,
    prepareHistoryDownload,
    downloadObjectByRequestId,
    getDownloadObjectUrl,
    stopMonitoring: stopMonitoringShortTermStorage,
} = useShortTermStorage();

const downloadTracker = useDownloadTracker();

const { confirm } = useConfirmDialog();

interface Props {
    historyId: string;
}

const props = defineProps<Props>();

const POLLING_DELAY = 3000;

const isLoadingRecords = ref(true);
const exportRecords = ref<ExportRecord[]>([]);
const history = ref<AnyHistory>();
const isLoadingHistory = ref(true);

const historyName = computed(() => history.value?.name ?? props.historyId);
const latestExportRecord = computed(() => (exportRecords.value?.length ? exportRecords.value.at(0) : null));
const previousExportRecords = computed(() => (exportRecords.value ? exportRecords.value.slice(1) : []));
const hasPreviousExports = computed(() => previousExportRecords.value?.length > 0);
const isBusy = computed(() => isLoadingRecords.value || isPreparingDownload.value || isExportTaskRunning.value);

const historyStore = useHistoryStore();

const isFatalError = ref(false);
const errorMessage = ref<string>();
const actionMessage = ref<string>();
const actionMessageVariant = ref<ColorVariant>();
const showOldRecords = ref(false);

onMounted(async () => {
    if (await loadHistory()) {
        updateExports();
    }
});

watch(isExportTaskRunning, (newValue, oldValue) => {
    const hasFinished = oldValue && !newValue;
    if (hasFinished) {
        updateExports();
    }
});

async function loadHistory() {
    isLoadingHistory.value = true;
    try {
        history.value =
            historyStore.getHistoryById(props.historyId, false) ??
            (await historyStore.loadHistoryById(props.historyId));
        return true;
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
        isFatalError.value = true;
        return false;
    } finally {
        isLoadingHistory.value = false;
    }
}

async function updateExports() {
    isLoadingRecords.value = true;
    try {
        errorMessage.value = undefined;
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
        errorMessage.value = errorMessageAsString(error);
    } finally {
        isLoadingRecords.value = false;
    }
}

async function onExportHistory(exportData: HistoryExportData) {
    switch (exportData.destination) {
        case "download":
            await prepareDownload(exportData);
            break;
        case "remote-source":
        case "rdm-repository":
        case "zenodo-repository":
            await exportToFileSource(exportData);
            break;
    }
}

async function exportToFileSource(exportData: HistoryExportData) {
    await exportHistoryToFileSource(props.historyId, exportData.remoteUri, exportData.outputFileName, exportData);
    updateExports();
}

async function prepareDownload(exportParams: ExportParams) {
    const result = await prepareHistoryDownload(props.historyId, {
        pollDelayInMs: POLLING_DELAY,
        exportParams: exportParams,
    });
    if (result) {
        downloadTracker.trackDownloadRequestWithData({
            taskId: result.storageRequestId,
            taskType: "short_term_storage",
            request: {
                source: "history-export",
                taskType: "short_term_storage",
                action: "export",
                object: {
                    id: props.historyId,
                    type: "history",
                    name: historyName.value,
                },
                description: `History export for ${historyName.value} for direct download`,
            },
            startedAt: new Date(),
            isFinal: false,
        });
    }
    updateExports();
}

function downloadFromRecord(record: ExportRecord) {
    if (record.canDownload) {
        downloadObjectByRequestId(record.stsDownloadId!);
    }
}

function copyDownloadLinkFromRecord(record: ExportRecord) {
    if (record.canDownload) {
        const relativeLink = getDownloadObjectUrl(record.stsDownloadId!);
        sendToClipboard(absPath(relativeLink), "Download link copied to your clipboard");
    }
}

async function reimportFromRecord(record: ExportRecord) {
    const confirmed = await confirm(
        `Do you really want to import a new copy of this history exported ${record.elapsedTime}?`
    );
    if (confirmed) {
        try {
            await reimportHistoryFromRecord(record);
            actionMessageVariant.value = "info";
            actionMessage.value =
                "The history is being imported in the background. Check your histories after a while to find it.";
        } catch (error) {
            actionMessageVariant.value = "danger";
            actionMessage.value = errorMessageAsString(error);
        }
    }
}

function onActionMessageDismissedFromRecord() {
    actionMessage.value = undefined;
    actionMessageVariant.value = undefined;
}

function onShowOldRecords() {
    showOldRecords.value = true;
}

onUnmounted(() => {
    stopWaitingForTask();
    stopMonitoringShortTermStorage();
});
</script>
<template>
    <div class="history-export-component">
        <Heading h1 separator inline>
            <FontAwesomeIcon :icon="faFileExport" class="text-primary float-left mr-2" />
            Export
            <b v-if="isFatalError" class="text-danger">Error</b>
            <LoadingSpan v-else-if="!history" spinner-only />
            <b v-else id="history-name">{{ historyName }}</b>
        </Heading>

        <BAlert v-if="isFatalError" id="fatal-error-alert" variant="danger" class="mt-3" show>
            {{ errorMessage }}
        </BAlert>

        <div v-if="history">
            <div v-if="latestExportRecord">
                <Heading h2 size="md">Latest Export Record</Heading>
                <ExportRecordDetails
                    v-if="latestExportRecord"
                    :record="latestExportRecord"
                    :action-message="actionMessage"
                    :action-message-variant="actionMessageVariant"
                    object-type="history"
                    @onDownload="downloadFromRecord"
                    @onCopyDownloadLink="copyDownloadLinkFromRecord"
                    @onReimport="reimportFromRecord"
                    @onActionMessageDismissed="onActionMessageDismissedFromRecord" />

                <GButton
                    v-if="hasPreviousExports"
                    id="show-old-records-button"
                    outline
                    color="blue"
                    @click="onShowOldRecords">
                    <FontAwesomeIcon :icon="faList" class="mr-1" />
                    Show old export records
                </GButton>

                <Heading h2 size="md" class="mt-3">Export your history again</Heading>
            </div>

            <HistoryExportWizard
                :history-id="props.historyId"
                :history-name="history.name"
                :is-busy="isBusy"
                @onExport="onExportHistory" />

            <BAlert v-if="errorMessage" id="last-export-record-error-alert" variant="danger" class="mt-3" show>
                {{ errorMessage }}
            </BAlert>
        </div>

        <GModal
            :show.sync="showOldRecords"
            :title="`Previous Export Records for ${historyName}`"
            size="medium"
            hide-header
            fixed-height
            class="history-export-old-records-modal"
            centered>
            <ExportRecordTable
                v-if="hasPreviousExports"
                id="previous-export-records"
                :records="previousExportRecords"
                class="mt-3"
                @onDownload="downloadFromRecord"
                @onReimport="reimportFromRecord" />
        </GModal>
    </div>
</template>
