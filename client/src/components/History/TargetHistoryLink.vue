<script setup lang="ts">
import { faHdd } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { useHistoryStore } from "@/stores/historyStore";

import SwitchToHistoryLink from "@/components/History/SwitchToHistoryLink.vue";

interface Props {
    targetHistoryId: string;
    targetHistoryCaption?: string;
}

const props = withDefaults(defineProps<Props>(), {
    targetHistoryCaption: "History",
});

const historyStore = useHistoryStore();
const { currentHistoryId } = storeToRefs(historyStore);

const isCurrentTargetHistory = computed(() => {
    return !!props.targetHistoryId && props.targetHistoryId === currentHistoryId.value;
});
</script>
<template>
    <span class="d-flex flex-gapx-1 align-items-center">
        <FontAwesomeIcon :icon="faHdd" />{{ props.targetHistoryCaption }}:

        <span v-if="props.targetHistoryId" class="history-link-wrapper d-flex flex-gapx-1 align-items-center">
            <SwitchToHistoryLink :history-id="props.targetHistoryId" />

            <span v-if="isCurrentTargetHistory" class="text-muted ml-1" data-description="current history indicator">
                (current)
            </span>
            <span
                v-else
                v-b-tooltip.hover.noninteractive
                data-description="not current history indicator"
                class="text-warning"
                title="This history is not your currently active history. You can click the link to switch to it.">
                (not current)
            </span>
        </span>
        <span v-else class="text-muted">Loading...</span>
    </span>
</template>
