<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { useExtendedHistory } from "@/composables/detailedHistory";
import { useHistoryStore } from "@/stores/historyStore";

import HistoryNavigation from "../CurrentHistory/HistoryNavigation.vue";
import CollectionPanel from "@/components/History/CurrentCollection/CollectionPanel.vue";
import HistoryPanel from "@/components/History/CurrentHistory/HistoryPanel.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faTimes);

interface Props {
    source: {
        id: string;
    };
    filter: string;
}

const props = defineProps<Props>();

const historyStore = useHistoryStore();
const { currentHistoryId, histories, historiesLoading, pinnedHistories } = storeToRefs(historyStore);

const { history } = useExtendedHistory(props.source.id);

const selectedCollections = ref<any[]>([]);

const sameToCurrent = computed(() => {
    return currentHistoryId.value === props.source.id;
});

function onViewCollection(collection: object) {
    selectedCollections.value = [...selectedCollections.value, collection];
}
</script>

<template>
    <div v-if="!history" class="container">
        <div class="row align-items-center h-100">
            <LoadingSpan class="mx-auto" message="Loading History" />
        </div>
    </div>

    <div v-else id="list-item" class="d-flex flex-column w-100">
        <div class="d-flex justify-content-between align-items-center">
            <div>
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
                    <FontAwesomeIcon :icon="faTimes" />
                    Hide
                </BButton>
            </div>
            <HistoryNavigation
                :history="history"
                :histories="histories"
                :histories-loading="historiesLoading"
                minimal />
        </div>

        <hr class="w-100 m-1" />

        <CollectionPanel
            v-if="selectedCollections.length && selectedCollections[0]?.history_id === source.id"
            :history="history"
            :selected-collections.sync="selectedCollections"
            :show-controls="false"
            @view-collection="onViewCollection" />

        <HistoryPanel
            v-else
            :history="history"
            :filter="filter"
            :show-controls="false"
            is-multi-view-item
            @view-collection="onViewCollection" />
    </div>
</template>
