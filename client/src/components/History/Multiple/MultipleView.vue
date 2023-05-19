<script setup lang="ts">
import { computed, ref, onMounted, type Ref } from "vue";
import { storeToRefs } from "pinia";
import localize from "@/utils/localization";
import { useUserStore } from "@/stores/userStore";
import { useHistoryStore } from "@/stores/historyStore";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import LoadingSpan from "@/components/LoadingSpan.vue";
import MultipleViewList from "./MultipleViewList.vue";
import SelectorModal from "@/components/History/Modals/SelectorModal.vue";

const filter = ref("");
const showSelectModal = ref(false);

library.add(faTimes);

const { currentUser } = storeToRefs(useUserStore());
const { histories, historiesLoading, currentHistory } = storeToRefs(useHistoryStore());

const historyStore = useHistoryStore();
onMounted(() => {
    historyStore.loadPinnedHistories();
});

const selectedHistories: Ref<{ id: string }[]> = computed(() => historyStore.pinnedHistories);

if (!selectedHistories.value.length ?? histories.value.length > 0) {
    historyStore.pinHistory(histories.value[0]!.id);
}

function addHistoriesToList(histories: { id: string }[]) {
    // Unpin histories that are already pinned but not in the incoming list
    const historiesToUnpin = selectedHistories.value.filter(
        (pinnedHistory) => !histories.some((history) => history.id === pinnedHistory.id)
    );
    historiesToUnpin.forEach((history) => {
        historyStore.unpinHistory(history.id);
    });
    // Pin histories that aren't already pinned and are in incoming list
    histories.forEach((history) => {
        const historyExists = selectedHistories.value.some((h) => h.id === history.id);
        if (!historyExists) {
            historyStore.pinHistory(history.id);
            historyStore.loadHistoryById(history.id);
        }
    });
}

function updateFilter(newFilter: string) {
    filter.value = newFilter;
}
</script>

<template>
    <div v-if="currentUser">
        <b-alert v-if="historiesLoading" class="m-2" variant="info" show>
            <LoadingSpan message="Loading Histories" />
        </b-alert>
        <div v-else-if="histories.length" class="multi-history-panel d-flex flex-column h-100">
            <b-input-group class="w-100">
                <b-form-input
                    v-model="filter"
                    size="sm"
                    debounce="500"
                    :class="filter && 'font-weight-bold'"
                    :placeholder="localize('search datasets in selected histories')"
                    data-description="filter text input"
                    @keyup.esc="updateFilter('')" />
                <b-input-group-append>
                    <b-button size="sm" data-description="show deleted filter toggle" @click="updateFilter('')">
                        <FontAwesomeIcon icon="fa-times" />
                    </b-button>
                </b-input-group-append>
            </b-input-group>
            <MultipleViewList
                :histories="histories"
                :filter="filter"
                :current-history="currentHistory"
                :selected-histories="selectedHistories"
                :show-modal.sync="showSelectModal" />
        </div>
        <b-alert v-else class="m-2" variant="danger" show>
            <span v-localize class="font-weight-bold">No History found.</span>
        </b-alert>
        <SelectorModal
            v-if="showSelectModal"
            :multiple="true"
            :histories="histories"
            :additional-options="['center', 'set-current']"
            :show-modal.sync="showSelectModal"
            title="Select histories"
            @selectHistories="addHistoriesToList" />
    </div>
</template>
