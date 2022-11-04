<script setup>
import { computed, ref, onMounted, watch } from "vue";
import { BAlert, BCard, BButton, BTab, BTabs } from "bootstrap-vue";
import LoadingSpan from "components/LoadingSpan";
import ExportRecordDetails from "components/Common/ExportRecordDetails.vue";
import ExportToFileSourceForm from "components/Common/ExportForm.vue";
import { HistoryExportService } from "./services";
import { useTaskMonitor } from "composables/useTaskMonitor";
import { useFileSources } from "composables/fileSources";
import { useShortTermStorage } from "composables/shortTermStorage";

const service = new HistoryExportService();

const { isRunning: isExportTaskRunning, waitForTask } = useTaskMonitor();
const { hasWritable: hasWritableFileSources } = useFileSources();
const { isPreparing: isPreparingDownload, downloadHistory } = useShortTermStorage();

const props = defineProps({
    historyId: {
        type: String,
        required: true,
    },
});

// TODO: make this configurable by the user?
const EXPORT_PARAMS = service.defaultExportParams;

const isLoadingRecords = ref(true);
const latestExportRecord = ref(null);
const isLatestExportReady = ref(false);
const previousExportRecords = ref(null);
const availableRecordsMessage = computed(() =>
    isLoadingRecords.value
        ? "Loading export records..."
        : "This history has no export records yet. You can choose one of the export options above."
);
const errorMessage = ref(null);

onMounted(async () => {
    updateExports();
});

watch(isExportTaskRunning, async () => {
    console.debug("Updating latest export after task finished");
    updateLatestExport();
});

async function updateLatestExport() {
    isLoadingRecords.value = true;
    const latestExport = await service.getLatestExportRecord(props.historyId);
    latestExportRecord.value = latestExport;
    isLatestExportReady.value = latestExport?.isReady;
    if (latestExport?.isPreparing) {
        isLatestExportReady.value = false;
        waitForTask(latestExport.taskUUID, 3000);
    }
    isLoadingRecords.value = false;
}

async function updateExports() {
    updateLatestExport();
    service.getExportRecords(props.historyId, { offset: 1, limit: 10 }).then((records) => {
        previousExportRecords.value = records;
    });
}

async function exportToFileSource(exportDirectory, fileName) {
    await service.exportToFileSource(props.historyId, exportDirectory, fileName, EXPORT_PARAMS);
    updateExports();
}

async function prepareDownload() {
    downloadHistory(props.historyId, { pollDelayInMs: 3000, exportParams: EXPORT_PARAMS });
    // updateExports();
}

function reimportHistoryFromRecord(record) {
    return service.reimportHistoryFromRecord(record);
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
                        If you need a `more permanent` way of storing your exported history you can export it directly
                        to one of the available remote file sources here.
                    </p>
                    <export-to-file-source-form what="history" @export="exportToFileSource" />
                </b-tab>
            </b-tabs>
        </b-card>

        <export-record-details
            v-if="latestExportRecord"
            :record="latestExportRecord"
            object-type="history"
            class="mt-3"
            @onReimport="reimportHistoryFromRecord" />
        <b-alert v-else-if="errorMessage" variant="danger" class="mt-3" show>
            {{ errorMessage }}
        </b-alert>
        <b-alert v-else variant="info" class="mt-3" show>
            {{ availableRecordsMessage }}
        </b-alert>
    </span>
</template>
