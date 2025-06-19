<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faArchive, faBurn } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import { type HistorySummary, userOwnsHistory } from "@/api";
import { Toast } from "@/composables/toast";
import { useEventStore } from "@/stores/eventStore";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";

import GLink from "@/components/BaseComponents/GLink.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faArchive, faBurn);

const router = useRouter();
const historyStore = useHistoryStore();
const userStore = useUserStore();

interface Props {
    historyId: string;
    filters?: Record<string, string | boolean>;
    inline?: boolean;
    thin?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    filters: undefined,
    inline: false,
    thin: true,
});

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
        return `${actionText.value} "${history.value?.name}"`;
    }
});

const tag = computed(() => {
    if (props.inline) {
        return "span";
    }
    return "div";
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

const linkClass = computed(() => {
    return props.inline ? ["history-link-inline"] : ["history-link"];
});
</script>

<template>
    <component :is="tag">
        <LoadingSpan v-if="!history" />
        <component :is="tag" v-else :class="linkClass" data-description="switch to history link">
            <GLink
                tooltip
                :thin="thin"
                data-description="switch to history link"
                :title="linkTitle"
                @click.stop="onClick($event, history)">
                {{ history.name }}
            </GLink>

            <FontAwesomeIcon v-if="history.purged" :icon="faBurn" fixed-width />
            <FontAwesomeIcon v-else-if="history.archived" :icon="faArchive" fixed-width />
        </component>
    </component>
</template>

<style scoped>
.history-link {
    display: flex;
    gap: 1px;
    align-items: center;
    justify-content: space-between;
}
</style>
