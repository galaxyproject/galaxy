<script setup lang="ts">
import { computed, ref } from "vue";
import { BAlert, BCard, BButton, BTab, BTabs } from "bootstrap-vue";
import { useFileSources } from "@/composables/fileSources";
import { faArchive } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { RouterLink } from "vue-router";
import HistoryArchiveExportSelector from "@/components/History/Archiving/HistoryArchiveExportSelector.vue";
import { useHistoryStore, type HistorySummary } from "@/stores/historyStore";
import LoadingSpan from "@/components/LoadingSpan.vue";
import { useToast } from "@/composables/toast";

library.add(faArchive);

const historyStore = useHistoryStore();
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

        <b-alert v-if="isHistoryAlreadyArchived" show variant="info">
            This history has been archived. You can access it from the
            <router-link :to="archivedHistoriesRoute">Archived Histories</router-link> section.
        </b-alert>
        <div v-else-if="history">
            <b-alert show variant="info">
                Archiving a history will remove it from your <i>active histories</i>. You can still access it from the
                <router-link :to="archivedHistoriesRoute">Archived Histories</router-link> section.
            </b-alert>

            <h2 class="h-md">How do you want to archive this history?</h2>
            <b-card no-body class="mt-3">
                <b-tabs pills card vertical lazy>
                    <b-tab id="keep-storage-tab" title="Keep storage space" active>
                        <p>
                            If you want to remove the history from your <i>active histories</i> but keep it around for
                            reference, you can move it to the
                            <router-link :to="archivedHistoriesRoute">Archived Histories</router-link> section, by
                            clicking the button below.
                        </p>
                        <p>
                            You can undo this action at any time, and the history will be moved back to your
                            <i>active histories</i>.
                        </p>

                        <b-button class="archive-history-btn mt-3" variant="primary" @click="onArchiveHistory()">
                            Archive history
                        </b-button>
                    </b-tab>
                    <b-tab v-if="hasWritableFileSources" id="free-storage-tab" title="Free storage space">
                        <history-archive-export-selector :history="history" @onArchive="onArchiveHistory" />
                    </b-tab>
                </b-tabs>
            </b-card>
        </div>
    </div>
</template>
