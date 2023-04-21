<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { BAlert, BCard, BButton, BCardText } from "bootstrap-vue";
import { exportToFileSource, getExportRecords } from "@/components/History/Export/services";
import LoadingSpan from "@/components/LoadingSpan.vue";
import ExportToFileSourceForm from "components/Common/ExportForm.vue";
import { DEFAULT_EXPORT_PARAMS } from "@/composables/shortTermStorage";
import type { ExportRecordModel } from "@/components/Common/models/exportRecordModel";
import type { HistoryDetailedModel } from "@/components/History/model";

interface HistoryExportSelectorProps {
    history: HistoryDetailedModel;
}

const props = defineProps<HistoryExportSelectorProps>();

const existingExports = ref<ExportRecordModel[]>([]);
const isLoading = ref(true);
const isExporting = ref(false);
const isExportDialogOpen = ref(false);
const isDeleteContentsConfirmed = ref(false);

const canCreateExportRecord = computed(() => {
    return !isLoading.value && !isExporting.value && !mostUpToDateExport.value;
});

const canArchiveHistory = computed(() => {
    return !isLoading.value && !isExporting.value && mostUpToDateExport.value && isDeleteContentsConfirmed.value;
});

const mostUpToDateExport = computed(() => {
    return existingExports.value.find((exportRecord) => !exportRecord.canExpire && exportRecord.isUpToDate);
});

const mostUpToDateExportIsReady = computed(() => {
    return mostUpToDateExport.value && mostUpToDateExport.value.isReady && mostUpToDateExport.value.canReimport;
});

onMounted(async () => {
    isLoading.value = true;
    await updateExports();
    isLoading.value = false;
});

async function updateExports() {
    existingExports.value = await getExportRecords(props.history.id);
    if (mostUpToDateExport.value) {
        console.log("Most up-to-date export record:", mostUpToDateExport.value);
        isExporting.value = mostUpToDateExport.value.isPreparing;
    }
}

async function onCreateExportRecord() {
    isExportDialogOpen.value = true;
}

async function doExportToFileSource(exportDirectory: string, fileName: string) {
    isExporting.value = true;
    isExportDialogOpen.value = false;

    // Prepend history ID to filename to avoid name collisions if multiple
    // histories are exported to the same directory with the same name
    const prefixedFileName = `${props.history.id}_${fileName}`;

    await exportToFileSource(props.history.id, exportDirectory, prefixedFileName, DEFAULT_EXPORT_PARAMS);
    updateExports();
}

async function archiveHistory() {
    console.log("TODO: archive history");
}
</script>

<template>
    <div>
        <p>
            If you are not planning to use this history in the near future, you can
            <b>archive and delete its contents to free up valuable disk space</b>.
        </p>
        <p>
            In order to be able to recover your archived history later, you need to export it first to a permanent
            remote location. Then you will be able to import it back to Galaxy from the remote source (as a new copy).
        </p>
        <b-alert v-if="isLoading" show variant="info">
            <loading-span message="Retrieving export records..." />
        </b-alert>
        <div v-else-if="mostUpToDateExport && mostUpToDateExportIsReady">
            <b-alert show variant="success">
                <p>
                    <b>There is an up-to-date export record of this history ready.</b>
                </p>
                <p>
                    This export record will be associated with your archived history so you can recover it later by
                    importing it.
                </p>
                <b-card class="mt-3">
                    <b-card-text>
                        <b>Exported {{ mostUpToDateExport.elapsedTime }}</b> on {{ mostUpToDateExport.date }}
                    </b-card-text>
                    <b-card-text> <b>Destination:</b> {{ mostUpToDateExport.importUri }} </b-card-text>
                </b-card>
            </b-alert>
        </div>
        <div v-else>
            <b-alert v-if="isExporting" show variant="info">
                <loading-span message="Generating export record. This may take a while..." />
            </b-alert>
            <b-alert v-else show variant="info">
                <p>
                    <b>
                        There is no up-to-date export record of this history. You need to create a new export record to
                        be able to recover the history later.
                    </b>
                </p>
                <p>Use the button below to create a new export record before archiving the history.</p>
                <b-button
                    class="export-history-btn"
                    :disabled="!canCreateExportRecord"
                    variant="primary"
                    @click="onCreateExportRecord">
                    Create export record
                </b-button>
            </b-alert>
        </div>
        <p v-if="!isDeleteContentsConfirmed" class="mt-3 mb-0">
            To continue, you need to confirm that you want to delete the contents of the original history before you can
            archive it using the checkbox below. No worries, you will be able to recover the history later by importing
            it from the export record above.
        </p>
        <b-form-checkbox v-model="isDeleteContentsConfirmed" class="my-3">
            <b>I am aware that the contents of the original history will be permanently deleted.</b>
        </b-form-checkbox>
        <b-alert show variant="warning">
            Remember that you cannot undo this action. Once you archive and delete the history, you can only recover it
            by importing it as a new copy from the export record.
        </b-alert>
        <b-button
            class="archive-history-btn mt-3"
            :disabled="!canArchiveHistory"
            variant="primary"
            @click="archiveHistory">
            Archive history
        </b-button>

        <b-modal v-model="isExportDialogOpen" title="Export history" size="lg" hide-footer>
            <ExportToFileSourceForm what="history" @export="doExportToFileSource" />
        </b-modal>
    </div>
</template>
