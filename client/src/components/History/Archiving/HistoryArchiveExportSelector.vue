<script setup lang="ts">
import { BAlert, BButton, BFormCheckbox, BModal } from "bootstrap-vue";
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";

import type { HistorySummary } from "@/api";
import { exportHistoryToFileSource, fetchHistoryExportRecords } from "@/api/histories.export";
import type { ExportRecord } from "@/components/Common/models/exportRecordModel";
import { DEFAULT_EXPORT_PARAMS } from "@/composables/shortTermStorage";
import { useTaskMonitor } from "@/composables/taskMonitor";

import ExportRecordCard from "./ExportRecordCard.vue";
import ExportToFileSourceForm from "@/components/Common/ExportForm.vue";
import ExportToRDMRepositoryForm from "@/components/Common/ExportRDMForm.vue";
import ExternalLink from "@/components/ExternalLink.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const {
    isRunning: isExportTaskRunning,
    waitForTask,
    requestHasFailed: taskMonitorRequestFailed,
    hasFailed: taskHasFailed,
} = useTaskMonitor();

interface HistoryExportSelectorProps {
    history: HistorySummary;
}

const props = defineProps<HistoryExportSelectorProps>();

const emit = defineEmits<{
    (e: "onArchive", exportRecordId: string): void;
}>();

const existingExports = ref<ExportRecord[]>([]);
const isLoading = ref(true);
const isExportingRecord = ref(false);
const isExportDialogOpen = ref(false);
const isDeleteContentsConfirmed = ref(false);
const exportErrorMessage = ref<string | null>(null);

const historyName = computed(() => {
    return props.history.name;
});

const mostUpToDateExport = computed(() => {
    return existingExports.value.find(
        (exportRecord) => exportRecord.isPermanent && (exportRecord.isUpToDate || exportRecord.isPreparing)
    );
});

const canCreateExportRecord = computed(() => {
    return !isLoading.value && !isExportTaskRunning.value && !mostUpToDateExport.value;
});

const canArchiveHistory = computed(() => {
    return (
        !isLoading.value && !isExportTaskRunning.value && mostUpToDateExport.value && isDeleteContentsConfirmed.value
    );
});

const mostUpToDateExportIsReady = computed(() => {
    return mostUpToDateExport.value && mostUpToDateExport.value.isReady && mostUpToDateExport.value.canReimport;
});

onMounted(async () => {
    isLoading.value = true;
    await updateExports();
    isLoading.value = false;
});

watch(isExportTaskRunning, (newValue, oldValue) => {
    isExportingRecord.value = newValue;
    const hasFinished = oldValue && !newValue;
    if (hasFinished) {
        updateExports();
    }
});

async function updateExports() {
    exportErrorMessage.value = null;
    try {
        existingExports.value = await fetchHistoryExportRecords(props.history.id);
        if (mostUpToDateExport.value) {
            const shouldWaitForTask =
                mostUpToDateExport.value?.isPreparing &&
                !isExportTaskRunning.value &&
                !taskMonitorRequestFailed.value &&
                !taskHasFailed.value;
            if (shouldWaitForTask) {
                waitForTask(mostUpToDateExport.value.taskUUID);
            }
            if (taskMonitorRequestFailed.value) {
                exportErrorMessage.value = "The request to get the export progress failed. Please check back later.";
            }
            if (taskHasFailed.value) {
                exportErrorMessage.value = "The history export request failed. Please try again later.";
            }
        }
    } catch (e) {
        exportErrorMessage.value = "The request to get your history exports records failed. Please check back later.";
    }
}

async function onCreateExportRecord() {
    isExportDialogOpen.value = true;
}

async function doExportToFileSourceWithPrefix(exportDirectory: string, fileName: string) {
    // Avoid name collisions if multiple different histories are exported to the
    // same destination with the same name
    const fileNameCompatibleUpdateTime = props.history.update_time.replace(/:/g, "-");
    const prefixedFileName = `${fileNameCompatibleUpdateTime}_${fileName}`;
    doExportToFileSource(exportDirectory, prefixedFileName);
}

async function doExportToFileSource(exportDirectory: string, fileName: string) {
    isExportingRecord.value = true;
    isExportDialogOpen.value = false;
    try {
        await exportHistoryToFileSource(props.history.id, exportDirectory, fileName, DEFAULT_EXPORT_PARAMS);
    } catch (error) {
        exportErrorMessage.value = "The history export request failed. Please try again later.";
    }
    updateExports();
}

function onArchiveHistoryWithExport() {
    if (mostUpToDateExport.value) {
        emit("onArchive", mostUpToDateExport.value.id);
    }
}
</script>

<template>
    <div>
        <p>
            If you are not planning to use this history in the near future, you can
            <b>archive and delete its contents to free up disk space</b>.
        </p>
        <p>
            To be able to recreate your archived history later, you need to export it first to a permanent remote
            location. Then you will be able to import it back to Galaxy from the remote source, as a new copy.
        </p>
        <BAlert v-if="isLoading" show variant="info">
            <LoadingSpan message="Retrieving export records..." />
        </BAlert>
        <BAlert v-else-if="exportErrorMessage" show variant="danger">
            <p>
                <b>Something went wrong</b>
            </p>
            <p>{{ exportErrorMessage }}</p>
        </BAlert>
        <div v-else-if="mostUpToDateExport && mostUpToDateExportIsReady">
            <BAlert show variant="success">
                <p>
                    <b>There is an up-to-date export record of this history ready.</b>
                </p>
                <p>
                    This export record will be associated with your archived history so you can recreate it later by
                    importing it.
                </p>
                <ExportRecordCard id="export-record-ready" class="mt-3" :export-record="mostUpToDateExport" />
            </BAlert>
        </div>
        <div v-else>
            <BAlert v-if="isExportingRecord" id="generating-export-record-alert" show variant="info">
                <LoadingSpan message="Generating export record. This may take a while..." />
            </BAlert>
            <BAlert v-else show variant="info">
                <p>
                    <b>
                        There is no up-to-date export record of this history. You need to create a new export record to
                        be able to recreate the history later.
                    </b>
                </p>
                <p>Use the button below to create a new export record before archiving the history.</p>
                <BButton
                    id="create-export-record-btn"
                    :disabled="!canCreateExportRecord"
                    variant="primary"
                    @click="onCreateExportRecord">
                    Create export record
                </BButton>
            </BAlert>
        </div>
        <p v-if="!isDeleteContentsConfirmed" class="mt-3 mb-0">
            To continue, you need to confirm that you want to delete the contents of the original history before you can
            archive it using the checkbox below. If you created an export record above, you will be able to recreate the
            history later by importing it from the export record.
        </p>
        <BFormCheckbox id="confirm-delete-checkbox" v-model="isDeleteContentsConfirmed" class="my-3">
            <b>I am aware that the contents of the original history will be permanently deleted.</b>
        </BFormCheckbox>
        <BAlert show variant="warning">
            Remember that you cannot undo this action. Once you archive and delete the history, you can only recover it
            by importing it as a new copy from the export record.
        </BAlert>
        <BButton
            id="archive-history-btn"
            class="mt-3"
            :disabled="!canArchiveHistory"
            variant="primary"
            @click="onArchiveHistoryWithExport">
            Archive (and purge) history
        </BButton>

        <BModal v-model="isExportDialogOpen" title="Export history to permanent storage" size="lg" hide-footer>
            <BTabs card vertical lazy class="export-option-tabs">
                <BTab id="to-remote-file-tab" title="To Repository" active>
                    <p>
                        <b>Exporting to a repository</b> will create a compressed archive of the history contents, copy
                        it to a remote location (e.g. an FTP server) and create an export record with this information
                        that will be associated with the archived history. You will be able to recreate the history
                        later by importing it from the export record.
                    </p>
                    <ExportToFileSourceForm what="history" @export="doExportToFileSourceWithPrefix" />
                </BTab>
                <BTab id="to-rdm-repository-tab" title="To RDM Repository">
                    <p>
                        <b>Exporting to a RDM repository</b> (e.g. any
                        <ExternalLink href="https://inveniosoftware.org/products/rdm/"> Invenio RDM </ExternalLink>
                        compatible repository) will require to create or select an existing record in the repository
                        where the history archive will be uploaded. The export record will be associated with the
                        archived history and you will be able to recreate the history later by importing it from the
                        export record.
                    </p>
                    <p>
                        You may need to setup your credentials for the selected repository in your
                        <RouterLink to="/user/information" target="_blank">settings page</RouterLink> to be able to
                        export.
                    </p>
                    <ExportToRDMRepositoryForm
                        what="history"
                        :default-filename="historyName + ' (Galaxy History)'"
                        :default-record-name="historyName"
                        @export="doExportToFileSource" />
                </BTab>
            </BTabs>
        </BModal>
    </div>
</template>
