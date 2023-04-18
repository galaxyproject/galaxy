<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { getExportRecords } from "@/components/History/Export/services";
import type { ExportRecordModel } from "@/components/Common/models/exportRecordModel";
import type { HistoryDetailedModel } from "@/components/History/model";

interface HistoryExportSelectorProps {
    history: HistoryDetailedModel;
}

const props = defineProps<HistoryExportSelectorProps>();

const existingExports = ref<ExportRecordModel[]>([]);
const isLoading = ref(true);
const isExporting = ref(false);

const mostUpToDateExport = computed(() => {
    return existingExports.value.find(
        (exportRecord) =>
            !exportRecord.canExpire && exportRecord.isUpToDate && exportRecord.isReady && exportRecord.canReimport
    );
});

onMounted(async () => {
    isLoading.value = true;
    existingExports.value = await getExportRecords(props.history.id);
    isLoading.value = false;
});

async function exportHistory() {
    console.log("TODO: export history");
}
</script>

<template>
    <div>
        <p>
            If you want to free up disk space by deleting the history contents, you can do so by exporting the history
            to a remote file source. If you want to recover your archived history later, you can import it from the
            remote source (as a new copy).
        </p>
        <div v-if="mostUpToDateExport">
            <b-alert show variant="success">
                <p>
                    <b>There is already an up-to-date export of this history.</b>
                </p>
                <p>
                    This export record will be associated with your archived history so you can recover it later by
                    importing it.
                </p>
                <b-card class="mt-3">
                    <b-card-text> <b>Exported on:</b> {{ mostUpToDateExport.date }} </b-card-text>
                    <b-card-text> <b>Exported to:</b> {{ mostUpToDateExport.importUri }} </b-card-text>
                </b-card>
            </b-alert>
        </div>
        <div v-else>
            <b-alert show variant="warning">
                <p>
                    <b>
                        There is no up-to-date export record of this history. You need to create a new export record to
                        be able to recover it later.
                    </b>
                </p>
                <p>Use the button below to create a new export record now.</p>
            </b-alert>
            <b-button class="export-history-btn" :disabled="isExporting" variant="primary" @click="exportHistory">
                Export history
            </b-button>
        </div>
    </div>
</template>
