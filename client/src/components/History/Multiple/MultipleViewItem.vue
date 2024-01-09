<script setup lang="ts">
import { BButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { useHistoryStore } from "@/stores/historyStore";

import CollectionPanel from "@/components/History/CurrentCollection/CollectionPanel.vue";
import HistoryPanel from "@/components/History/CurrentHistory/HistoryPanel.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    source: {
        id: string;
    };
    filter: string;
}

const props = defineProps<Props>();

const historyStore = useHistoryStore();
const { currentHistoryId, pinnedHistories } = storeToRefs(historyStore);

const selectedCollections = ref<any[]>([]);

const sameToCurrent = computed(() => {
    return currentHistoryId.value === props.source.id;
});
const getHistory = computed(() => {
    return historyStore.getHistoryById(props.source.id);
});

function onViewCollection(collection: object) {
    selectedCollections.value = [...selectedCollections.value, collection];
}
</script>

<template>
    <div v-if="!getHistory" class="container">
        <div class="row align-items-center h-100">
            <LoadingSpan class="mx-auto" message="Loading History" />
        </div>
    </div>

    <div v-else id="list-item" class="d-flex flex-column align-items-center w-100">
        <CollectionPanel
            v-if="selectedCollections.length && selectedCollections[0]?.history_id === source.id"
            :history="getHistory"
            :selected-collections.sync="selectedCollections"
            :show-controls="false"
            @view-collection="onViewCollection" />

        <HistoryPanel
            v-else
            :history="getHistory"
            :filter="filter"
            :show-controls="false"
            is-multi-view-item
            @view-collection="onViewCollection" />

        <hr class="w-100 m-2" />

        <div class="flex-row flex-grow-0">
            <BButton
                size="sm"
                class="my-1"
                :disabled="sameToCurrent"
                :variant="sameToCurrent ? 'disabled' : 'outline-info'"
                :title="sameToCurrent ? 'Current History' : 'Switch to this history'"
                @click="historyStore.setCurrentHistory(source.id)">
                {{ sameToCurrent ? "Current History" : "Switch to" }}
            </BButton>
            <BButton
                v-if="Object.keys(pinnedHistories).length > 0"
                size="sm"
                class="my-1"
                variant="outline-danger"
                title="Hide this history from the list"
                @click="historyStore.unpinHistories([source.id])">
                Hide
            </BButton>
        </div>
    </div>
</template>
