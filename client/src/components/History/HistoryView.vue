<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, ref, watch } from "vue";

import { CollectionEntry } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import CollectionPanel from "./CurrentCollection/CollectionPanel.vue";
import HistoryPanel from "./CurrentHistory/HistoryPanel.vue";
import CopyModal from "./Modals/CopyModal.vue";

type TODO = any;

const props = defineProps<{ id: string }>();

const historyStore = useHistoryStore();

historyStore.loadHistoryById(props.id);

const { currentUser } = storeToRefs(useUserStore());
const { currentHistory } = storeToRefs(useHistoryStore());
const selectedCollections = ref<TODO[]>([]);
const history = ref<TODO>();

onMounted(async () => {
    await historyStore.loadHistoryById(props.id);
    const newHistoryValue = historyStore.getHistoryById(props.id);
    if (newHistoryValue) {
        history.value = newHistoryValue;
    }
});

watch(
    () => props.id,
    (newValue) => {
        const newHistoryValue = historyStore.getHistoryById(newValue);
        if (newHistoryValue) {
            history.value = newHistoryValue;
        }
    }
);

const userOwnsHistory = computed(() => {
    if (!currentUser.value || !history.value) {
        return false;
    }

    if (!("id" in currentUser.value)) {
        return false;
    }

    return currentUser.value.id === history.value.user_id;
});

const isCurrentHistory = computed(() => {
    return currentHistory.value?.id === history.value?.id;
});

const isSetAsCurrentDisabled = computed(() => {
    return isCurrentHistory.value || history.value?.archived || history.value?.purged;
});

const setAsCurrentTitle = computed(() => {
    if (isCurrentHistory.value) {
        return "This history is already your current history.";
    }

    if (history.value?.archived) {
        return "This history has been archived and cannot be set as your current history. Unarchive it first.";
    }

    if (history.value?.purged) {
        return "This history has been purged and cannot be set as your current history.";
    }

    return "Switch to this history";
});

const canEditHistory = computed(() => {
    return userOwnsHistory.value && !history.value?.archived && !history.value?.purged;
});

const showHistoryArchived = computed(() => {
    return history.value?.archived && userOwnsHistory.value;
});

const showHistoryStateInfo = computed(() => {
    return showHistoryArchived.value || history.value?.purged;
});

const historyStateInfoMessage = computed(() => {
    if (showHistoryArchived.value && history.value?.purged) {
        return "This history has been archived and purged.";
    }

    if (showHistoryArchived.value) {
        return "This history has been archived.";
    }

    if (history.value?.purged) {
        return "This history has been purged.";
    }

    return "";
});

const canImportHistory = computed(() => {
    return !userOwnsHistory.value && !history.value?.purged;
});

const shouldDisplayCollectionPanel = computed(() => {
    return selectedCollections.value.length && selectedCollections.value[0].history_id === props.id;
});

function onViewCollection(collection: CollectionEntry) {
    selectedCollections.value = [...selectedCollections.value, collection];
}
</script>

<template>
    <div v-if="currentUser && history" class="d-flex flex-column h-100">
        <b-alert v-if="showHistoryStateInfo" variant="info" show data-description="history state info">
            {{ historyStateInfoMessage }}
        </b-alert>

        <div class="flex-row flex-grow-0 pb-3">
            <b-button
                v-if="userOwnsHistory"
                size="sm"
                variant="outline-info"
                :title="setAsCurrentTitle"
                :disabled="isSetAsCurrentDisabled"
                data-description="switch to history button"
                @click="historyStore.setCurrentHistory(history.id)">
                Switch to this history
            </b-button>

            <b-button
                v-if="canImportHistory"
                v-b-modal:copy-history-modal
                size="sm"
                variant="outline-info"
                title="Import this history"
                data-description="import history button">
                Import this history
            </b-button>
        </div>

        <CollectionPanel
            v-if="shouldDisplayCollectionPanel"
            :history="history"
            :selected-collections.sync="selectedCollections"
            :show-controls="false"
            @view-collection="onViewCollection" />
        <HistoryPanel
            v-else
            :history="history"
            :can-edit-history="canEditHistory"
            :should-show-controls="false"
            filterable
            @view-collection="onViewCollection" />

        <CopyModal id="copy-history-modal" :history="history" />
    </div>
</template>
