<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { BAlert, BCard, BButton, BTab, BTabs } from "bootstrap-vue";
import { useFileSources } from "@/composables/fileSources";
import { faArchive } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { RouterLink } from "vue-router";
import HistoryExportSelector from "./HistoryExportSelector.vue";
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

const currentTab = ref(0);

const isFreeStorageTabActive = computed(() => currentTab.value === 1);
const isArchiveDisabled = computed(
    () => isArchiving.value || (isFreeStorageTabActive.value && !hasWritableFileSources.value)
);

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
        <h1 class="h-lg">Archive history {{ props.historyId }}</h1>

        <b-alert show variant="info">
            Archiving a history will remove it from your <i>active histories</i>. You can still access it from the
            <RouterLink to="TODO">Archived Histories</RouterLink> section.
        </b-alert>

        <p>
            When archiving a history, you can choose to keep the history contents on disk or to free up disk space by
            permanently deleting the history contents.
            <b>No worries, you can always recover your archived history later</b>.
        </p>

        <b-card v-if="history" no-body class="mt-3">
            <b-tabs v-model="currentTab" pills card>
                <b-tab id="keep-storage-tab" title="Keep storage space" active>
                    <p>
                        If you just want to move the history to the
                        <RouterLink to="TODO">Archived Histories</RouterLink> section, you can do so by clicking the
                        button below. The history will be moved to the archive, but its contents will remain on disk.
                    </p>
                </b-tab>
                <b-tab v-if="hasWritableFileSources" id="free-storage-tab" title="Free storage space">
                    <HistoryExportSelector :history="history" />
                </b-tab>
            </b-tabs>
        </b-card>

        <b-button
            class="archive-history-btn mt-3"
            :disabled="isArchiveDisabled"
            variant="primary"
            @click="archiveHistory">
            Archive history
        </b-button>
    </div>
</template>
