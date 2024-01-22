<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faArchive } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BCard, BTab, BTabs } from "bootstrap-vue";
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";

import type { HistorySummary } from "@/api";
import { useConfig } from "@/composables/config";
import { useFileSources } from "@/composables/fileSources";
import { useToast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";

import HistoryArchiveExportSelector from "@/components/History/Archiving/HistoryArchiveExportSelector.vue";
import HistoryArchiveSimple from "@/components/History/Archiving/HistoryArchiveSimple.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faArchive);

const historyStore = useHistoryStore();
const { config } = useConfig(true);
const toast = useToast();

const { hasWritable: hasWritableFileSources } = useFileSources();

interface ArchiveHistoryWizardProps {
    historyId: string;
}

const props = defineProps<ArchiveHistoryWizardProps>();

const isArchiving = ref(false);

const history = computed<HistorySummary | null>(() => {
    const history = historyStore.getHistoryById(props.historyId);
    if (history === null) {
        // It could be already an archived history, so we won't find it in the store
        // as it's not in the active histories anymore.
        historyStore.loadHistoryById(props.historyId);
        return historyStore.getHistoryById(props.historyId);
    }
    return history;
});

const isHistoryAlreadyArchived = computed(() => {
    return history.value?.archived;
});

const canFreeStorage = computed(() => {
    return hasWritableFileSources.value && config.value.enable_celery_tasks;
});

const archivedHistoriesRoute = "/histories/archived";

async function onArchiveHistory(exportRecordId?: string) {
    isArchiving.value = true;
    try {
        const shouldPurge = exportRecordId !== undefined;
        await historyStore.archiveHistoryById(props.historyId, exportRecordId, shouldPurge);
        toast.success("History archived successfully.");
    } catch (error) {
        toast.error(`The history archive request failed. Please try again later. Reason: ${error}`);
    } finally {
        isArchiving.value = false;
    }
}
</script>

<template>
    <div class="history-archive-wizard">
        <FontAwesomeIcon icon="archive" size="2x" class="text-primary float-left mr-2" />
        <h1 class="h-lg">
            Archive
            <LoadingSpan v-if="!history" spinner-only />
            <b v-else>{{ history.name }}</b>
        </h1>

        <BAlert v-if="isHistoryAlreadyArchived" id="history-archived-alert" show variant="success">
            This history has been archived. You can access it from the
            <RouterLink :to="archivedHistoriesRoute">Archived Histories</RouterLink> section.
        </BAlert>
        <div v-else-if="history">
            <BAlert show variant="info">
                Archiving a history will remove it from your <i>active histories</i>. You can still access it from the
                <RouterLink :to="archivedHistoriesRoute">Archived Histories</RouterLink> section.
            </BAlert>

            <div v-if="canFreeStorage">
                <h2 class="h-md">How do you want to archive this history?</h2>
                <BCard no-body class="mt-3">
                    <BTabs pills card vertical lazy class="archival-option-tabs">
                        <BTab id="keep-storage-tab" title="Keep storage space" active>
                            <HistoryArchiveSimple :history="history" @onArchive="onArchiveHistory" />
                        </BTab>
                        <BTab id="free-storage-tab" title="Free storage space">
                            <HistoryArchiveExportSelector :history="history" @onArchive="onArchiveHistory" />
                        </BTab>
                    </BTabs>
                </BCard>
            </div>
            <HistoryArchiveSimple v-else :history="history" @onArchive="onArchiveHistory" />
        </div>
    </div>
</template>
