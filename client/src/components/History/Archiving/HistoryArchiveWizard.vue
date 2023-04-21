<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { BAlert, BCard, BButton, BTab, BTabs } from "bootstrap-vue";
import { useFileSources } from "@/composables/fileSources";
import { faArchive } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { RouterLink } from "vue-router";
import HistoryArchiveExportSelector from "@/components/History/Archiving/HistoryArchiveExportSelector.vue";
import { getHistoryById } from "@/store/historyStore/model/queries";
import type { HistoryDetailedModel } from "@/components/History/model";

const { hasWritable: hasWritableFileSources } = useFileSources();

interface ArchiveHistoryWizardProps {
    historyId: string;
}

const props = defineProps<ArchiveHistoryWizardProps>();

//@ts-ignore bad library types
library.add(faArchive);

const history = ref<HistoryDetailedModel | null>(null);
const isArchiving = ref(false);

const historyName = computed(() => history.value?.name ?? props.historyId);

const goToArchivedHistoriesLink = computed(() => {
    return "TODO";
});

onMounted(async () => {
    //TODO: replace with store
    history.value = await getHistoryById(props.historyId);
});

async function archiveHistory() {
    isArchiving.value = true;
    try {
        console.log("TODO: archive history");
    } catch (error) {
        console.error(error);
    } finally {
        isArchiving.value = false;
    }
}
</script>

<template>
    <div class="history-archive-wizard">
        <font-awesome-icon icon="archive" size="2x" class="text-primary float-left mr-2" />
        <h1 class="h-lg">
            Archive <b>{{ historyName }}</b>
        </h1>

        <b-alert show variant="info">
            Archiving a history will remove it from your <i>active histories</i>. You can still access it from the
            <router-link :to="goToArchivedHistoriesLink">Archived Histories</router-link> section.
        </b-alert>

        <h2 class="h-md">How do you want to archive this history?</h2>
        <b-card v-if="history" no-body class="mt-3">
            <b-tabs pills card vertical lazy>
                <b-tab id="keep-storage-tab" title="Keep storage space" active>
                    <p>
                        If you want to remove the history from your <i>active histories</i> but keep it around for
                        reference, you can move it to the
                        <router-link :to="goToArchivedHistoriesLink">Archived Histories</router-link> section, by
                        clicking the button below.
                    </p>
                    <p>
                        You can undo this action at any time, and the history will be moved back to your
                        <i>active histories</i>.
                    </p>

                    <b-button class="archive-history-btn mt-3" variant="primary" @click="archiveHistory">
                        Archive history
                    </b-button>
                </b-tab>
                <b-tab v-if="hasWritableFileSources" id="free-storage-tab" title="Free storage space">
                    <history-archive-export-selector :history="history" />
                </b-tab>
            </b-tabs>
        </b-card>
    </div>
</template>
