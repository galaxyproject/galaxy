<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { BAlert, BButton, BFormCheckbox, BModal } from "bootstrap-vue";
import { exportToFileSource, getExportRecords } from "@/components/History/Export/services";
import LoadingSpan from "@/components/LoadingSpan.vue";
import ExportToFileSourceForm from "@/components/Common/ExportForm.vue";
import { DEFAULT_EXPORT_PARAMS } from "@/composables/shortTermStorage";
import type { ExportRecord } from "@/components/Common/models/exportRecordModel";
import { useTaskMonitor } from "@/composables/taskMonitor";
import type { HistorySummary } from "@/stores/historyStore";
import ExportRecordCard from "./ExportRecordCard.vue";

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
        existingExports.value = await getExportRecords(props.history.id);
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

async function doExportToFileSource(exportDirectory: string, fileName: string) {
    isExportingRecord.value = true;
    isExportDialogOpen.value = false;

    // Avoid name collisions if multiple different histories are exported to the
    // same destination with the same name
    const prefixedFileName = `${props.history.id}_${fileName}`;

    try {
        await exportToFileSource(props.history.id, exportDirectory, prefixedFileName, DEFAULT_EXPORT_PARAMS);
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
        <b-alert v-if="isLoading" show variant="info">
            <loading-span message="Retrieving export records..." />
        </b-alert>
        <b-alert v-else-if="exportErrorMessage" show variant="danger">
            <p>
                <b>Something went wrong</b>
            </p>
            <p>{{ exportErrorMessage }}</p>
        </b-alert>
        <div v-else-if="mostUpToDateExport && mostUpToDateExportIsReady">
            <b-alert show variant="success">
                <p>
                    <b>There is an up-to-date export record of this history ready.</b>
                </p>
                <p>
                    This export record will be associated with your archived history so you can recreate it later by
                    importing it.
                </p>
                <ExportRecordCard id="export-record-ready" class="mt-3" :export-record="mostUpToDateExport" />
            </b-alert>
        </div>
        <div v-else>
            <b-alert v-if="isExportingRecord" id="generating-export-record-alert" show variant="info">
                <loading-span message="Generating export record. This may take a while..." />
            </b-alert>
            <b-alert v-else show variant="info">
                <p>
                    <b>
                        There is no up-to-date export record of this history. You need to create a new export record to
                        be able to recreate the history later.
                    </b>
                </p>
                <p>Use the button below to create a new export record before archiving the history.</p>
                <b-button
                    id="create-export-record-btn"
                    :disabled="!canCreateExportRecord"
                    variant="primary"
                    @click="onCreateExportRecord">
                    Create export record
                </b-button>
            </b-alert>
        </div>
        <p v-if="!isDeleteContentsConfirmed" class="mt-3 mb-0">
            To continue, you need to confirm that you want to delete the contents of the original history before you can
            archive it using the checkbox below. If you created an export record above, you will be able to recreate the
            history later by importing it from the export record.
        </p>
        <b-form-checkbox id="confirm-delete-checkbox" v-model="isDeleteContentsConfirmed" class="my-3">
            <b>I am aware that the contents of the original history will be permanently deleted.</b>
        </b-form-checkbox>
        <b-alert show variant="warning">
            Remember that you cannot undo this action. Once you archive and delete the history, you can only recover it
            by importing it as a new copy from the export record.
        </b-alert>
        <b-button
            id="archive-history-btn"
            class="mt-3"
            :disabled="!canArchiveHistory"
            variant="primary"
            @click="onArchiveHistoryWithExport">
            Archive (and purge) history
        </b-button>

        <b-modal v-model="isExportDialogOpen" title="Export history to permanent storage" size="lg" hide-footer>
            <ExportToFileSourceForm what="history" @export="doExportToFileSource" />
        </b-modal>
    </div>
</template>
