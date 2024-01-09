<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheckSquare, faClock, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { Toast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";

import MultipleViewList from "./MultipleViewList.vue";
import SelectorModal from "@/components/History/Modals/SelectorModal.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

type PinnedHistory = { id: string };

const filter = ref("");
const showSelectModal = ref(false);
const initialLoaded = ref(false);

library.add(faClock, faCheckSquare, faTimes);

const { currentUser } = storeToRefs(useUserStore());
const { histories, currentHistory, historiesLoading } = storeToRefs(useHistoryStore());

const historyStore = useHistoryStore();

const selectedHistories = computed<PinnedHistory[]>(() => {
    if (hasPinnedHistories.value) {
        return historyStore.pinnedHistories;
    } else {
        // get the latest four histories
        return [...histories.value]
            .sort((a, b) => {
                if (a.update_time < b.update_time) {
                    return 1;
                } else {
                    return -1;
                }
            })
            .slice(0, 4)
            .map((history) => {
                return { id: history.id };
            });
    }
});

// On mounted, wait for history store to load, then set `initialLoaded` to true
watch(
    () => historiesLoading.value,
    (loading: boolean) => {
        if (!loading && histories.value.length > 0 && !initialLoaded.value) {
            initialLoaded.value = true;
        }
    },
    { immediate: true }
);

/** computed ref that indicates whether the user has histories pinned */
const hasPinnedHistories = computed(() => Object.keys(historyStore.pinnedHistories).length > 0);

/**
 * From the incoming list, pin histories that are not already pinned and
 * unpin histories that are not in the incoming list.
 * This is a mechanism to allow users to select or deselect histories in modal.
 * @param incomingHistories the incoming list of histories to pin
 */
function addHistoriesToList(incomingHistories: PinnedHistory[]) {
    if (incomingHistories.length === 0) {
        showRecent();
        return;
    }
    // Pin histories that are in incoming list and aren't already pinned
    incomingHistories.forEach((history) => {
        const historyExists = historyStore.pinnedHistories.some((h: PinnedHistory) => h.id === history.id);
        if (!historyExists) {
            historyStore.pinHistory(history.id);
            historyStore.loadHistoryById(history.id);
        }
    });
    // Unpin histories that are already pinned but not in the incoming list
    const historiesToUnpin = historyStore.pinnedHistories
        .filter((pinnedHistory: PinnedHistory) => !incomingHistories.some((history) => history.id === pinnedHistory.id))
        .map((history: PinnedHistory) => history.id);
    historyStore.unpinHistories(historiesToUnpin);
}

const showRecentTitle = computed(() => {
    if (hasPinnedHistories.value) {
        return localize("Show 4 most recently updated histories instead");
    } else {
        return localize("Currently showing 4 most recently updated histories");
    }
});

/** Reset to _default_ state; showing 4 latest updated histories */
function showRecent() {
    historyStore.pinnedHistories = [];
    Toast.info(
        "Showing the 4 most recently updated histories. Pin histories to this view by clicking on Select Histories."
    );
}

function updateFilter(newFilter: string) {
    filter.value = newFilter;
}
</script>

<template>
    <div v-if="currentUser">
        <b-alert v-if="!initialLoaded && historiesLoading" class="m-2" variant="info" show>
            <LoadingSpan message="Loading Histories" />
        </b-alert>
        <div v-else-if="histories.length" class="multi-history-panel d-flex flex-column h-100">
            <div class="d-flex justify-content-between">
                <div class="w-100">
                    <b-input-group>
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
                                <FontAwesomeIcon icon="fa-times" fixed-width />
                            </b-button>
                        </b-input-group-append>
                    </b-input-group>
                </div>
                <b-button-group v-b-tooltip.hover.noninteractive :title="showRecentTitle">
                    <b-button
                        size="sm"
                        data-description="show recent histories"
                        class="text-nowrap ml-1"
                        :disabled="!hasPinnedHistories"
                        @click="showRecent">
                        <FontAwesomeIcon icon="fa-clock" />
                        <span v-localize>Show Recent</span>
                    </b-button>
                </b-button-group>
                <b-button
                    size="sm"
                    data-description="open select histories modal"
                    class="text-nowrap ml-1"
                    @click="showSelectModal = true">
                    <FontAwesomeIcon icon="fa-check-square" />
                    <span v-localize>Select Histories</span>
                </b-button>
            </div>
            <MultipleViewList
                :filter="filter"
                :current-history="currentHistory"
                :selected-histories="selectedHistories"
                :show-modal.sync="showSelectModal" />
        </div>
        <b-alert v-else-if="!histories.length" class="m-2" variant="danger" show>
            <span v-localize class="font-weight-bold">No History found.</span>
        </b-alert>
        <SelectorModal
            v-show="showSelectModal"
            :multiple="true"
            :histories="histories"
            :additional-options="['center', 'set-current']"
            :show-modal.sync="showSelectModal"
            title="Select/Deselect histories"
            @selectHistories="addHistoriesToList" />
    </div>
</template>
