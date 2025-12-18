<script setup lang="ts">
import { faChevronRight, faExchangeAlt, faPlus, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { ref } from "vue";

import type { HistorySummary } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";

import GButton from "@/components/BaseComponents/GButton.vue";
import HistoryOptions from "@/components/History/HistoryOptions.vue";
import SelectorModal from "@/components/History/Modals/SelectorModal.vue";

interface Props {
    history: HistorySummary;
    minimal?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    minimal: false,
});

const emit = defineEmits<{
    (e: "show", showPanel: boolean): void;
}>();

const historyStore = useHistoryStore();
const { histories, changingCurrentHistory } = storeToRefs(historyStore);

const showSwitchModal = ref(false);

const userStore = useUserStore();

const { isAnonymous } = storeToRefs(userStore);

function userTitle(title: string) {
    if (isAnonymous.value) {
        return localize("Log in to") + " " + localize(title);
    } else {
        return localize(title);
    }
}
</script>

<template>
    <div>
        <nav
            :class="{ 'd-flex justify-content-between mx-3 my-2': !props.minimal }"
            aria-label="current history management">
            <GButton v-if="!props.minimal" size="small" transparent @click="emit('show', false)">
                <FontAwesomeIcon fixed-width :icon="faChevronRight" />
                <span>History</span>
            </GButton>

            <BButtonGroup>
                <BButton
                    v-if="!props.minimal"
                    v-b-tooltip.top.hover.noninteractive
                    class="create-hist-btn"
                    data-description="create new history"
                    size="sm"
                    variant="link"
                    :disabled="isAnonymous"
                    :title="userTitle('Create new history')"
                    @click="historyStore.createNewHistory">
                    <FontAwesomeIcon fixed-width :icon="faPlus" />
                </BButton>

                <BButton
                    v-if="!props.minimal"
                    v-b-tooltip.top.hover.noninteractive
                    data-description="switch to another history"
                    size="sm"
                    variant="link"
                    :disabled="isAnonymous || changingCurrentHistory"
                    :title="userTitle('Switch to history')"
                    @click="showSwitchModal = !showSwitchModal">
                    <FontAwesomeIcon
                        fixed-width
                        :icon="changingCurrentHistory ? faSpinner : faExchangeAlt"
                        :spin="changingCurrentHistory" />
                </BButton>

                <HistoryOptions :history="history" :minimal="props.minimal" />
            </BButtonGroup>
        </nav>

        <SelectorModal
            v-if="!props.minimal"
            id="selector-history-modal"
            :histories="histories"
            :additional-options="['center', 'multi']"
            :show-modal.sync="showSwitchModal"
            @selectHistory="historyStore.setCurrentHistory($event.id)" />
    </div>
</template>
