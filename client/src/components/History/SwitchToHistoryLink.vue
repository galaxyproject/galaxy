<script setup lang="ts">
import { BLink } from "bootstrap-vue";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import { HistorySummary } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";

import LoadingSpan from "@/components/LoadingSpan.vue";

const router = useRouter();
const historyStore = useHistoryStore();

interface Props {
    historyId: string;
}

const props = defineProps<Props>();

const history = computed(() => historyStore.getHistoryById(props.historyId));
const canSwitch = computed(() => !!history.value && !history.value.archived && !history.value.purged);
const actionText = computed(() => (canSwitch.value ? "Switch to" : "View in new tab"));

function onClick(history: HistorySummary) {
    console.log("onClick", history);
    if (canSwitch.value) {
        console.log("setCurrentHistory", history.id);
        historyStore.setCurrentHistory(history.id);
        return;
    }
    console.log("viewHistoryInNewTab", history);
    viewHistoryInNewTab(history);
}

function viewHistoryInNewTab(history: HistorySummary) {
    const routeData = router.resolve(`/histories/view?id=${history.id}`);
    window.open(routeData.href, "_blank");
}
</script>

<template>
    <div>
        <LoadingSpan v-if="!history" />
        <div v-else v-b-tooltip.hover.top.html :title="`<b>${actionText}</b><br>${history.name}`" class="truncate">
            <BLink class="history-link" href="#" @click.stop="onClick(history)">
                {{ history.name }}
            </BLink>
        </div>
    </div>
</template>
