<script setup lang="ts">
import { ref } from "vue";
import { storeToRefs } from "pinia";
import localize from "@/utils/localization";
import { useUserStore } from "@/stores/userStore";
import { useHistoryStore } from "@/stores/historyStore";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import LoadingSpan from "@/components/LoadingSpan.vue";
import MultipleViewList from "./MultipleViewList.vue";

const filter = ref("");

//@ts-ignore bad library types
library.add(faTimes);

const { currentUser } = storeToRefs(useUserStore());
const { histories, historiesLoading, currentHistory } = storeToRefs(useHistoryStore());

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
            <MultipleViewList :histories="histories" :filter="filter" :current-history="currentHistory" />
        </div>
        <b-alert v-else class="m-2" variant="danger" show>
            <span v-localize class="font-weight-bold">No History found.</span>
        </b-alert>
    </div>
</template>
