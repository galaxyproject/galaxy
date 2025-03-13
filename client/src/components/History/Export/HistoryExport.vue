<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faFileExport } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BCard, BTab, BTabs } from "bootstrap-vue";
import { computed, onMounted, ref, watch } from "vue";

import type { AnyHistory } from "@/api";
import {
    exportHistoryToFileSource,
    fetchHistoryExportRecords,
    reimportHistoryFromRecord,
} from "@/api/histories.export";
import type { ColorVariant } from "@/components/Common";
import { areEqual, type ExportParams, type ExportRecord } from "@/components/Common/models/exportRecordModel";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useFileSources } from "@/composables/fileSources";
import { DEFAULT_EXPORT_PARAMS, useShortTermStorage } from "@/composables/shortTermStorage";
import { useTaskMonitor } from "@/composables/taskMonitor";
import { useHistoryStore } from "@/stores/historyStore";
import { copy as sendToClipboard } from "@/utils/clipboard";
import { absPath } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import ExportOptions from "./ExportOptions.vue";
import ExportToFileSourceForm from "@/components/Common/ExportForm.vue";
import ExportToRDMRepositoryForm from "@/components/Common/ExportRDMForm.vue";
import ExportRecordDetails from "@/components/Common/ExportRecordDetails.vue";
import ExportRecordTable from "@/components/Common/ExportRecordTable.vue";
import RDMCredentialsInfo from "@/components/Common/RDMCredentialsInfo.vue";
import ExternalLink from "@/components/ExternalLink.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const {
    isRunning: isExportTaskRunning,
    waitForTask,
    requestHasFailed: taskMonitorRequestFailed,
    hasFailed: taskHasFailed,
} = useTaskMonitor();

const { hasWritable: hasWritableFileSources } = useFileSources({ exclude: ["rdm"] });
const {
    hasWritable: hasWritableRDMFileSources,
    getFileSourceById,
    getFileSourcesByType,
    isPrivateFileSource,
} = useFileSources({ include: ["rdm"] });

const {
    isPreparing: isPreparingDownload,
    prepareHistoryDownload,
    downloadObjectByRequestId,
    getDownloadObjectUrl,
} = useShortTermStorage();

const { confirm } = useConfirmDialog();

interface Props {
    historyId: string;
}

const props = defineProps<Props>();

library.add(faFileExport);

const POLLING_DELAY = 3000;

const exportParams = ref(DEFAULT_EXPORT_PARAMS);
const isLoadingRecords = ref(true);
const exportRecords = ref<ExportRecord[]>([]);
const history = ref<AnyHistory>();
const isLoadingHistory = ref(true);

const historyName = computed(() => history.value?.name ?? props.historyId);
const defaultFileName = computed(() => `(Galaxy History) ${historyName.value}`);
const latestExportRecord = computed(() => (exportRecords.value?.length ? exportRecords.value.at(0) : null));
const isLatestExportRecordReadyToDownload = computed(
    () =>
        latestExportRecord.value &&
        latestExportRecord.value.isUpToDate &&
        latestExportRecord.value.canDownload &&
        areEqual(latestExportRecord.value.exportParams, exportParams.value)
);
const canGenerateDownload = computed(() => !isPreparingDownload.value && !isLatestExportRecordReadyToDownload.value);
const previousExportRecords = computed(() => (exportRecords.value ? exportRecords.value.slice(1) : []));
const hasPreviousExports = computed(() => previousExportRecords.value?.length > 0);
const availableRecordsMessage = computed(() =>
    isLoadingRecords.value
        ? "Loading export records..."
        : "This history has no export records yet. You can choose one of the export options above."
);

const historyStore = useHistoryStore();

const isFatalError = ref(false);
const errorMessage = ref<string>();
const actionMessage = ref<string>();
const actionMessageVariant = ref<ColorVariant>();
const zenodoSource = computed(() => getZenodoSource());

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

function getZenodoSource() {
    const zenodoSources = getFileSourcesByType("zenodo");
    // Prioritize the one provided by the user in case there are multiple
    return zenodoSources.find((fs) => isPrivateFileSource(fs) && fs.writable) ?? getFileSourceById("zenodo");
}

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

async function doExportToFileSource(exportDirectory: string, fileName: string) {
    await exportHistoryToFileSource(props.historyId, exportDirectory, fileName, exportParams.value);
    updateExports();
}

async function prepareDownload() {
    await prepareHistoryDownload(props.historyId, { pollDelayInMs: POLLING_DELAY, exportParams: exportParams.value });
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

function updateExportParams(newParams: ExportParams) {
    exportParams.value = {
        ...newParams,
    };
}
</script>
<template>
    <span class="history-export-component">
        <FontAwesomeIcon icon="file-export" size="2x" class="text-primary float-left mr-2" />
        <h1 class="h-lg">
            Export
            <b v-if="isFatalError" class="text-danger">Error</b>
            <LoadingSpan v-else-if="!history" spinner-only />
            <b v-else id="history-name">{{ historyName }}</b>
        </h1>

        <BAlert v-if="isFatalError" id="fatal-error-alert" variant="danger" class="mt-3" show>
            {{ errorMessage }}
        </BAlert>
        <div v-if="history">
            <ExportOptions
                id="history-export-options"
                class="mt-3"
                :export-params="exportParams"
                @onValueChanged="updateExportParams" />

            <h2 class="h-md mt-3">How do you want to export this history?</h2>
            <BCard no-body class="mt-3">
                <BTabs pills card vertical>
                    <BTab
                        id="direct-download-tab"
                        title="to direct download"
                        title-link-class="tab-export-to-link"
                        active>
                        <p>
                            Here you can generate a temporal download for your history. When your download link expires
                            or your history changes you can re-generate it again.
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
                            The latest export record is ready. Use the download button below to download it or change
                            the advanced export options above to generate a new one.
                        </BAlert>
                    </BTab>
                    <BTab
                        v-if="hasWritableFileSources"
                        id="file-source-tab"
                        title="to remote file"
                        title-link-class="tab-export-to-file">
                        <p>
                            If you need a "more permanent" way of storing your history archive you can export it
                            directly to one of the available repositories. You will be able to re-import it
                            later as long as it remains available on the remote server.
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

                        <RDMCredentialsInfo what="history export archive" />

                        <ExportToRDMRepositoryForm
                            what="history"
                            :default-filename="defaultFileName"
                            :default-record-name="historyName"
                            :clear-input-after-export="true"
                            @export="doExportToFileSource" />
                    </BTab>
                    <BTab
                        v-if="zenodoSource"
                        id="zenodo-file-source-tab"
                        :title="`to ${zenodoSource.label}`"
                        title-link-class="tab-export-to-zenodo-repo">
                        <div class="zenodo-info">
                            <img
                                src="https://raw.githubusercontent.com/zenodo/zenodo/master/zenodo/modules/theme/static/img/logos/zenodo-gradient-square.svg"
                                alt="ZENODO Logo" />
                            <p>
                                <ExternalLink href="https://zenodo.org"><b>Zenodo</b></ExternalLink> is a
                                general-purpose open repository developed under the
                                <ExternalLink href="https://www.openaire.eu">European OpenAIRE</ExternalLink> program
                                and operated by <ExternalLink href="https://home.cern">CERN</ExternalLink>. It allows
                                researchers to deposit research papers, data sets, research software, reports, and any
                                other research related digital artefacts. For each submission, a persistent
                                <b>digital object identifier (DOI)</b> is minted, which makes the stored items easily
                                citeable.
                            </p>
                        </div>

                        <RDMCredentialsInfo
                            what="history export archive"
                            :selected-repository="zenodoSource"
                            :is-private-file-source="isPrivateFileSource(zenodoSource)" />
                        <ExportToRDMRepositoryForm
                            what="history"
                            :default-filename="defaultFileName"
                            :default-record-name="historyName"
                            :clear-input-after-export="true"
                            :file-source="zenodoSource"
                            @export="doExportToFileSource">
                        </ExportToRDMRepositoryForm>
                    </BTab>
                </BTabs>
            </BCard>

            <BAlert v-if="errorMessage" id="last-export-record-error-alert" variant="danger" class="mt-3" show>
                {{ errorMessage }}
            </BAlert>
            <div v-else-if="latestExportRecord">
                <h2 class="h-md mt-3">Export Records</h2>
                <BCard>
                    <ExportRecordDetails
                        :record="latestExportRecord"
                        object-type="history"
                        :action-message="actionMessage"
                        :action-message-variant="actionMessageVariant"
                        @onDownload="downloadFromRecord"
                        @onCopyDownloadLink="copyDownloadLinkFromRecord"
                        @onReimport="reimportFromRecord"
                        @onActionMessageDismissed="onActionMessageDismissedFromRecord" />
                    <ExportRecordTable
                        v-if="hasPreviousExports"
                        id="previous-export-records"
                        :records="previousExportRecords"
                        class="mt-3"
                        @onDownload="downloadFromRecord"
                        @onReimport="reimportFromRecord" />
                </BCard>
            </div>
            <BAlert v-else id="no-export-records-alert" variant="info" class="mt-3" show>
                {{ availableRecordsMessage }}
            </BAlert>
        </div>
    </span>
</template>

<style scoped>
.zenodo-info {
    display: flex;
    align-items: start;
    gap: 0.5rem;
}
</style>
