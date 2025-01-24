<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faArchive, faBurn } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BLink } from "bootstrap-vue";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import { type HistorySummary, userOwnsHistory } from "@/api";
import { Toast } from "@/composables/toast";
import { useEventStore } from "@/stores/eventStore";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";

import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faArchive, faBurn);

const router = useRouter();
const historyStore = useHistoryStore();
const userStore = useUserStore();

interface Props {
    historyId: string;
    filters?: Record<string, string | boolean>;
}

const props = defineProps<Props>();

const history = computed(() => historyStore.getHistoryById(props.historyId));

const canSwitch = computed(
    () =>
        !!history.value &&
        !history.value.archived &&
        !history.value.purged &&
        userOwnsHistory(userStore.currentUser, history.value)
);

const actionText = computed(() => {
    if (canSwitch.value) {
        if (props.filters) {
            return "Show in history";
        }
        return "Switch to";
    }
    return "View in new tab";
});

const linkTitle = computed(() => {
    if (historyStore.currentHistoryId === props.historyId) {
        return "This is your current history";
    } else {
        return `<b>${actionText.value}</b><br>${history.value?.name}`;
    }
});

async function onClick(event: MouseEvent, history: HistorySummary) {
    const eventStore = useEventStore();
    const ctrlKey = eventStore.isMac ? event.metaKey : event.ctrlKey;
    if (!ctrlKey && historyStore.currentHistoryId === history.id) {
        return;
    }
    if (!ctrlKey && canSwitch.value) {
        if (props.filters) {
            historyStore.applyFilters(history.id, props.filters);
        } else {
            try {
                await historyStore.setCurrentHistory(history.id);
            } catch (error) {
                Toast.error(errorMessageAsString(error));
            }
        }
        return;
    }
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
        <div v-else class="history-link" data-description="switch to history link">
            <BLink
                v-b-tooltip.hover.top.noninteractive.html
                data-description="switch to history link"
                class="truncate"
                href="#"
                :title="linkTitle"
                @click.stop="onClick($event, history)">
                {{ history.name }}
            </BLink>

            <FontAwesomeIcon v-if="history.purged" :icon="faBurn" fixed-width />
            <FontAwesomeIcon v-else-if="history.archived" :icon="faArchive" fixed-width />
        </div>
    </div>
</template>

<style scoped>
.history-link {
    display: flex;
    gap: 1px;
    align-items: center;
    justify-content: space-between;
}
</style>
