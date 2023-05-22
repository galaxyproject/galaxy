<script setup lang="ts">
import { computed, ref } from "vue";
import { BAlert, BCard, BTab, BTabs } from "bootstrap-vue";
import { useFileSources } from "@/composables/fileSources";
import { faArchive } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { RouterLink } from "vue-router";
import HistoryArchiveExportSelector from "@/components/History/Archiving/HistoryArchiveExportSelector.vue";
import HistoryArchiveSimple from "@/components/History/Archiving/HistoryArchiveSimple.vue";
import { useHistoryStore, type HistorySummary } from "@/stores/historyStore";
import LoadingSpan from "@/components/LoadingSpan.vue";
import { useConfig } from "@/composables/config";
import { useToast } from "@/composables/toast";

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
        <font-awesome-icon icon="archive" size="2x" class="text-primary float-left mr-2" />
        <h1 class="h-lg">
            Archive
            <loading-span v-if="!history" spinner-only />
            <b v-else>{{ history.name }}</b>
        </h1>

        <b-alert v-if="isHistoryAlreadyArchived" id="history-archived-alert" show variant="success">
            This history has been archived. You can access it from the
            <router-link :to="archivedHistoriesRoute">Archived Histories</router-link> section.
        </b-alert>
        <div v-else-if="history">
            <b-alert show variant="info">
                Archiving a history will remove it from your <i>active histories</i>. You can still access it from the
                <router-link :to="archivedHistoriesRoute">Archived Histories</router-link> section.
            </b-alert>

            <div v-if="canFreeStorage">
                <h2 class="h-md">How do you want to archive this history?</h2>
                <b-card no-body class="mt-3">
                    <b-tabs pills card vertical lazy class="archival-option-tabs">
                        <b-tab id="keep-storage-tab" title="Keep storage space" active>
                            <history-archive-simple :history="history" @onArchive="onArchiveHistory" />
                        </b-tab>
                        <b-tab id="free-storage-tab" title="Free storage space">
                            <history-archive-export-selector :history="history" @onArchive="onArchiveHistory" />
                        </b-tab>
                    </b-tabs>
                </b-card>
            </div>
            <history-archive-simple v-else :history="history" @onArchive="onArchiveHistory" />
        </div>
    </div>
</template>
