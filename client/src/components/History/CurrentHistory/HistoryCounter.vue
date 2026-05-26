<script setup lang="ts">
import {
    faBook,
    faDatabase,
    faEyeSlash,
    faMapMarker,
    faSpinner,
    faSync,
    faTrash,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { watchImmediate } from "@vueuse/core";
import { BButton, BButtonGroup } from "bootstrap-vue";
import { formatDistanceToNowStrict } from "date-fns";
import { storeToRefs } from "pinia";
import prettyBytes from "pretty-bytes";
import { computed, onMounted, ref, toRef } from "vue";
import { useRouter } from "vue-router/composables";

import { type HistorySummaryExtended, userOwnsHistory } from "@/api";
import { HistoryFilters } from "@/components/History/HistoryFilters.js";
import { PAGE_LABELS } from "@/components/Page/constants";
import { useConfig } from "@/composables/config";
import { useHistoryContentStats } from "@/composables/historyContentStats";
import { useToast } from "@/composables/toast";
import { useSSEConnectionStatus } from "@/composables/useNotificationSSE";
import { useWindowAwareNavigation } from "@/composables/windowAwareNavigation";
import { usePageEditorStore } from "@/stores/pageEditorStore";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";

import GButton from "@/components/BaseComponents/GButton.vue";

const props = withDefaults(
    defineProps<{
        history: HistorySummaryExtended;
        isWatching?: boolean;
        lastChecked: Date;
        filterText?: string;
        showControls?: boolean;
        hideReload?: boolean;
    }>(),
    {
        isWatching: false,
        lastChecked: () => new Date(),
        filterText: "",
        showControls: false,
        hideReload: false,
    },
);

const emit = defineEmits(["update:filter-text", "reloadContents"]);

const router = useRouter();
const { pushToFrameOrPage } = useWindowAwareNavigation();
const { currentUser, isAnonymous } = storeToRefs(useUserStore());
const { config } = useConfig();
const { connected: sseConnected, hasEverConnected: sseHasEverConnected } = useSSEConnectionStatus();
const { historySize, numItemsActive, numItemsDeleted, numItemsHidden } = useHistoryContentStats(
    toRef(props, "history"),
);

const sseMode = computed(() => config.value?.enable_sse_updates === true);
// Treat the connection as "lost" only after a successful open: the brief
// initial-connect window where ``sseConnected`` is still false isn't a
// real outage and shouldn't go red.
const sseLost = computed(() => sseMode.value && sseHasEverConnected.value && !sseConnected.value);

const reloadButtonLoading = ref(false);
const reloadButtonTitle = ref("");
const reloadButtonVariant = ref("link");
const historyPreferredObjectStoreId = ref<string | null | undefined>();

watchImmediate(
    () => props.history,
    () => (historyPreferredObjectStoreId.value = props.history.preferred_object_store_id),
);

const niceHistorySize = computed(() => prettyBytes(historySize.value));
const canManageStorage = computed(() => !isAnonymous.value && userOwnsHistory(currentUser.value, props.history));

function onDashboard() {
    router.push({ name: "HistoryOverviewInAnalysis", params: { historyId: props.history.id } });
}

function setFilter(filter: string) {
    let newFilterText = "";
    let settings = {};
    if (filter == "") {
        settings = {
            deleted: false,
            visible: true,
        };
    } else {
        const newVal = getCurrentFilterVal(filter) === "any" ? HistoryFilters.defaultFilters[filter] : "any";
        settings = {
            deleted: filter === "deleted" ? newVal : getCurrentFilterVal("deleted"),
            visible: filter === "visible" ? newVal : getCurrentFilterVal("visible"),
        };
    }
    newFilterText = HistoryFilters.applyFiltersToText(settings, props.filterText);
    emit("update:filter-text", newFilterText);
}

function getCurrentFilterVal(filter: string) {
    return HistoryFilters.getFilterValue(props.filterText, filter);
}

function updateTime() {
    if (sseMode.value) {
        // Under SSE the "last checked" timestamp ticks only when the history
        // actually changes — a 2-minute idle window is normal and shouldn't
        // be presented as staleness. Surface a connection-lost warning
        // instead, gated on a previous successful open.
        if (sseLost.value) {
            reloadButtonTitle.value = "Live updates disconnected. Click to refresh.";
            reloadButtonVariant.value = "danger";
        } else {
            reloadButtonTitle.value = "Refresh history";
            reloadButtonVariant.value = "link";
        }
        return;
    }
    const diffToNow = formatDistanceToNowStrict(props.lastChecked, { addSuffix: true });
    const diffToNowSec = Date.now().valueOf() - props.lastChecked.valueOf();
    // if history isn't being watched or hasn't been watched/polled for over 2 minutes
    if (!props.isWatching || diffToNowSec > 120000) {
        reloadButtonTitle.value = "Last refreshed " + diffToNow + ". Consider reloading the page.";
        reloadButtonVariant.value = "danger";
    } else {
        reloadButtonTitle.value = "Last refreshed " + diffToNow;
        reloadButtonVariant.value = "link";
    }
}

async function reloadContents() {
    emit("reloadContents");
    reloadButtonLoading.value = true;
    setTimeout(() => {
        reloadButtonLoading.value = false;
    }, 1000);
}

// Re-render the button as soon as the SSE state flips, instead of waiting up
// to a second for the next setInterval tick — connection-loss feedback should
// be immediate.
watchImmediate([sseMode, sseLost], updateTime);

const isResolvingPage = ref(false);

async function navigateToCurrentPage() {
    const pageStore = usePageEditorStore();
    const toast = useToast();
    isResolvingPage.value = true;
    try {
        const pageId = await pageStore.resolveCurrentPage(props.history.id);
        const page = pageStore.pages.find((n) => n.id === pageId);
        const pageTitle = page?.title || PAGE_LABELS.history.entityName;
        const inlineUrl = `/histories/${props.history.id}/pages/${pageId}`;
        pushToFrameOrPage({
            framedUrl: `${inlineUrl}?displayOnly=true`,
            inlineUrl,
            title: `${PAGE_LABELS.history.entityName}: ${pageTitle}`,
        });
    } catch (e: any) {
        toast.error(e.message || "Failed to open page");
    } finally {
        isResolvingPage.value = false;
    }
}

onMounted(() => {
    // The polling-mode title is derived from a wall-clock diff that has no
    // reactive dependency, so a 1s tick keeps "Last refreshed Xs ago" fresh.
    setInterval(updateTime, 1000);
});
</script>

<template>
    <div class="history-size my-1 d-flex justify-content-between">
        <div class="d-flex">
            <GButton
                tooltip
                :title="localize('History Size')"
                transparent
                size="small"
                color="blue"
                class="rounded-0 history-storage-overview-button"
                :disabled="!canManageStorage"
                data-description="storage dashboard button"
                @click="onDashboard">
                <FontAwesomeIcon :icon="faDatabase" />
                <span>{{ niceHistorySize }}</span>
            </GButton>

            <GButton
                tooltip
                :title="PAGE_LABELS.history.historyCounterTooltip"
                transparent
                size="small"
                color="blue"
                class="rounded-0"
                :disabled="isAnonymous || isResolvingPage"
                data-description="history page button"
                @click="navigateToCurrentPage">
                <FontAwesomeIcon :icon="isResolvingPage ? faSpinner : faBook" :spin="isResolvingPage" />
            </GButton>
        </div>

        <BButtonGroup v-if="currentUser">
            <BButtonGroup>
                <BButton
                    v-g-tooltip.hover
                    :title="localize('Show active')"
                    variant="link"
                    size="sm"
                    class="rounded-0 text-decoration-none"
                    data-description="show active items button"
                    @click="setFilter('')">
                    <FontAwesomeIcon :icon="faMapMarker" />
                    <span>{{ numItemsActive }}</span>
                </BButton>

                <BButton
                    v-if="numItemsDeleted"
                    v-g-tooltip.hover
                    :title="localize('Include deleted')"
                    variant="link"
                    size="sm"
                    class="rounded-0 text-decoration-none"
                    :pressed="getCurrentFilterVal('deleted') !== false"
                    data-description="include deleted items button"
                    @click="setFilter('deleted')">
                    <FontAwesomeIcon :icon="faTrash" />
                    <span>{{ numItemsDeleted }}</span>
                </BButton>

                <BButton
                    v-if="numItemsHidden"
                    v-g-tooltip.hover
                    :title="localize('Include hidden')"
                    variant="link"
                    size="sm"
                    class="rounded-0 text-decoration-none"
                    :pressed="getCurrentFilterVal('visible') !== true"
                    data-description="include hidden items button"
                    @click="setFilter('visible')">
                    <FontAwesomeIcon :icon="faEyeSlash" />
                    <span>{{ numItemsHidden }}</span>
                </BButton>

                <BButton
                    v-if="!hideReload"
                    v-g-tooltip.hover
                    :title="reloadButtonTitle"
                    :variant="reloadButtonVariant"
                    size="sm"
                    class="rounded-0 text-decoration-none history-refresh-button"
                    @click="reloadContents()">
                    <FontAwesomeIcon :icon="faSync" :spin="reloadButtonLoading" />
                </BButton>
            </BButtonGroup>
        </BButtonGroup>
    </div>
</template>

<style lang="scss" scoped>
.btn {
    white-space: nowrap;
}
</style>
