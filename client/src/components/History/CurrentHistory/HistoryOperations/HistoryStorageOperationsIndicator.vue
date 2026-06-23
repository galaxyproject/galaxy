<script setup lang="ts">
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BLink, BPopover } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onUnmounted, ref, watch } from "vue";

import { useStorageHistoryRunsWatcher } from "@/composables/useStorageRunWatcher";
import { useUserFlagsStore } from "@/stores/userFlagsStore";
import localize from "@/utils/localization";

import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";

interface Props {
    historyId: string;
    showSelection: boolean;
    activeStorageRunCount: number;
}

const props = defineProps<Props>();

const userFlagsStore = useUserFlagsStore();
const { showStorageOperationsHelperPopover } = storeToRefs(userFlagsStore);

const isStorageHelperVisible = ref(false);

const hasActiveStorageRuns = computed(() => props.activeStorageRunCount > 0);
const storageOperationsRoute = computed(() => `/histories/${props.historyId}/storage/runs`);
const storageOperationsButtonId = computed(() => `history-storage-operations-${props.historyId}`);
const { startPolling, stopPolling } = useStorageHistoryRunsWatcher(props.historyId);

watch(
    [hasActiveStorageRuns, () => props.showSelection],
    ([hasRuns, showSelection]) => {
        isStorageHelperVisible.value = hasRuns && !showSelection && showStorageOperationsHelperPopover.value;
    },
    { immediate: true },
);

watch(
    hasActiveStorageRuns,
    (hasRuns) => {
        if (hasRuns) {
            startPolling();
        } else {
            stopPolling();
        }
    },
    { immediate: true },
);

onUnmounted(() => {
    stopPolling();
});

function onDoNotShowAgain() {
    userFlagsStore.ignoreStorageOperationsHelperPopover();
    isStorageHelperVisible.value = false;
}
</script>

<template>
    <div v-if="!showSelection && hasActiveStorageRuns">
        <GButtonGroup>
            <GButton
                :id="storageOperationsButtonId"
                tooltip
                :title="localize('Background operations are running')"
                class="rounded-0"
                size="small"
                color="blue"
                transparent
                :to="storageOperationsRoute">
                <FontAwesomeIcon :icon="faSpinner" spin fixed-width />
            </GButton>
        </GButtonGroup>

        <BPopover
            :show.sync="isStorageHelperVisible"
            :target="storageOperationsButtonId"
            triggers="manual hover"
            placement="bottomleft"
            boundary="window">
            <div class="d-flex flex-column flex-gapx-1">
                <span>{{ localize("Background operations are running. Click this spinner to open status.") }}</span>
                <BLink @click="onDoNotShowAgain">{{ localize("Do not show this again") }}</BLink>
            </div>
        </BPopover>
    </div>
</template>
