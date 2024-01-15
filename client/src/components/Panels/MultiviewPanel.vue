<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faColumns, faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import { HistoriesFilters } from "@/components/History/HistoriesFilters";
import { Toast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import { localize } from "@/utils/localization";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import FilterMenu from "@/components/Common/FilterMenu.vue";
import HistoryList from "@/components/History/HistoryScrollList.vue";

const route = useRoute();
const router = useRouter();

// @ts-ignore bad library types
library.add(faColumns, faUndo);

const filter = ref("");
const showAdvanced = ref(false);
const loading = ref(false);

const isAnonymous = computed(() => useUserStore().isAnonymous);
const historyStore = useHistoryStore();
const { histories, historiesLoading, currentHistoryId } = storeToRefs(historyStore);

const pinnedHistoryCount = computed(() => {
    return Object.keys(historyStore.pinnedHistories).length;
});

const pinRecentTitle = computed(() => {
    if (pinnedHistoryCount.value > 0) {
        return localize("Reset selection to show 4 most recently updated histories instead");
    } else {
        return localize("Currently showing 4 most recently updated histories in Multiview");
    }
});

const pinRecentText = computed(() => {
    if (pinnedHistoryCount.value > 1) {
        return localize(`${pinnedHistoryCount.value} histories pinned. Click here to reset`);
    } else if (pinnedHistoryCount.value == 1) {
        return localize("1 history pinned. Click here to reset");
    } else {
        return localize("Select histories to pin to Multiview");
    }
});

async function createAndPin() {
    try {
        loading.value = true;
        await historyStore.createNewHistory();
        if (!currentHistoryId.value) {
            throw new Error("Error creating history");
        }
        historyStore.pinHistory(currentHistoryId.value);
        router.push("/histories/view_multiple");
    } catch (error: any) {
        console.error(error);
        Toast.error(errorMessageAsString(error), "Error creating and pinning history");
    } finally {
        loading.value = false;
    }
}

/** Reset to _default_ state; showing 4 latest updated histories */
function pinRecent() {
    historyStore.pinnedHistories = [];
    Toast.info(
        "Showing the 4 most recently updated histories in Multiview. Pin histories to History Multiview by selecting them in the panel.",
        "History Multiview"
    );
}

function setFilter(newFilter: string, newValue: string) {
    filter.value = HistoriesFilters.setFilterValue(filter.value, newFilter, newValue);
}

function userTitle(title: string) {
    if (isAnonymous.value == true) {
        return `Log in to ${title}`;
    } else {
        return title;
    }
}
</script>

<template>
    <div class="unified-panel" aria-labelledby="multiview-heading">
        <div unselectable="on">
            <div class="unified-panel-header-inner">
                <nav class="d-flex justify-content-between mx-3 my-2">
                    <h2 v-localize class="m-1 h-sm">Select Histories</h2>
                    <b-button-group>
                        <b-button
                            v-b-tooltip.bottom.hover
                            data-description="create new history and pin"
                            size="sm"
                            variant="link"
                            :title="userTitle('Create new history and pin to multiview')"
                            :disabled="isAnonymous"
                            @click="createAndPin">
                            <Icon fixed-width icon="plus" />
                        </b-button>
                    </b-button-group>
                </nav>
            </div>
        </div>
        <div class="unified-panel-controls">
            <FilterMenu
                class="mb-3"
                name="Histories"
                placeholder="search histories"
                :filter-class="HistoriesFilters"
                :filter-text.sync="filter"
                :loading="historiesLoading || loading"
                :show-advanced.sync="showAdvanced" />
            <section v-if="!showAdvanced">
                <b-button
                    v-if="route.path !== '/histories/view_multiple'"
                    v-b-tooltip.hover.noninteractive.bottom
                    :aria-label="userTitle('Open History Multiview in center panel')"
                    :title="userTitle('Open History Multiview in center panel')"
                    class="w-100 mb-2"
                    size="sm"
                    :disabled="isAnonymous"
                    @click="router.push('/histories/view_multiple')">
                    <FontAwesomeIcon icon="columns" />
                    <span v-localize>Open History Multiview</span>
                </b-button>
                <b-button-group
                    v-else
                    v-b-tooltip.hover.noninteractive.bottom
                    class="w-100 mb-2"
                    :aria-label="pinRecentTitle"
                    :title="pinRecentTitle">
                    <b-button size="sm" :disabled="!pinnedHistoryCount" @click="pinRecent">
                        <span class="position-relative">
                            <FontAwesomeIcon v-if="pinnedHistoryCount" icon="undo" class="mr-1" />
                            <b>{{ pinRecentText }}</b>
                        </span>
                    </b-button>
                </b-button-group>
            </section>
        </div>
        <div v-if="isAnonymous">
            <b-badge class="alert-info w-100 mx-2">
                Please <a :href="withPrefix('/login')">log in or register</a> to create multiple histories.
            </b-badge>
        </div>
        <HistoryList
            v-show="!showAdvanced"
            multiple
            :filter="filter"
            :histories="histories"
            :loading.sync="loading"
            @setFilter="setFilter" />
    </div>
</template>
