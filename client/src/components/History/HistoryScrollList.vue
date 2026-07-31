<script setup lang="ts">
import { faListAlt } from "@fortawesome/free-regular-svg-icons";
import { faArchive, faBurn, faColumns, faSignInAlt, faTrash } from "@fortawesome/free-solid-svg-icons";
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { type AnyHistory, type HistorySummary, userOwnsHistory } from "@/api";
import type { CardAction, CardBadge } from "@/components/Common/GCard.types";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import { HistoriesFilters } from "./HistoriesFilters";

import GCard from "@/components/Common/GCard.vue";
import ScrollList from "@/components/ScrollList/ScrollList.vue";

type AdditionalOptions = "set-current" | "multi" | "center";
type PinnedHistory = { id: string };

interface Props {
    multiple?: boolean;
    selectedHistories?: PinnedHistory[];
    /** Id of the row to mark as `current` (the Invocations-style highlight).
     *  Undefined falls back to the store's currentHistoryId; pass `null` to
     *  suppress the highlight entirely. */
    currentItemId?: string | null;
    /** When true, drop deleted and purged histories from the rendered list. */
    hideDeleted?: boolean;
    additionalOptions?: AdditionalOptions[];
    showModal?: boolean;
    inModal?: boolean;
    filter: string;
    loading: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    multiple: false,
    selectedHistories: () => [],
    currentItemId: undefined,
    hideDeleted: false,
    additionalOptions: () => [],
    showModal: false,
    inModal: false,
    filter: "",
    loading: false,
});

const emit = defineEmits<{
    (e: "selectHistory", history: HistorySummary): void;
    (e: "setFilter", filter: string, value: string): void;
    (e: "update:loading", loading: boolean): void;
    (e: "update:show-modal", showModal: boolean): void;
}>();

const busy = ref(false);

const historyStore = useHistoryStore();
const { currentHistoryId, histories, totalHistoryCount, pinnedHistories, allHistoriesLoaded } =
    storeToRefs(historyStore);
const { currentUser } = storeToRefs(useUserStore());

const effectiveCurrentId = computed(() =>
    props.currentItemId === undefined ? currentHistoryId.value : props.currentItemId,
);

/** How many matches to put in the DOM at a time.
 *
 * The list is not virtualized: every item handed to ScrollList becomes a card.
 * Rendering thousands at once is what made the panel stall, to the point that
 * the search box could not be typed in and no result could be clicked, so the
 * matches are held in memory but revealed a window at a time.
 */
const RENDER_PAGE_SIZE = 50;
const renderLimit = ref(RENDER_PAGE_SIZE);

const hasNoResults = computed(() => props.filter && filtered.value.length == 0);
/** The matches actually rendered, as opposed to all of the ones that matched. */
const visible = computed(() => filtered.value.slice(0, renderLimit.value));
const serverExhausted = computed(
    () => allHistoriesLoaded.value || totalHistoryCount.value <= historiesProxy.value.length,
);

onMounted(async () => {
    // if mounted with a filter, the whole list is needed to search it
    if (props.filter !== "") {
        await historyStore.loadAllHistories();
    }
});

watch(
    () => props.filter,
    async (newVal: string, oldVal: string) => {
        if (newVal === oldVal) {
            return;
        }
        // A new search starts at the top of its own results.
        renderLimit.value = RENDER_PAGE_SIZE;
        // Searching happens against the locally held list, so the list only has
        // to be fetched once rather than queried again on every change of the
        // text. Matching a few thousand names in the browser is immediate.
        if (newVal !== "") {
            await historyStore.loadAllHistories();
        }
    },
);

watch(
    () => busy.value,
    (loading: boolean) => {
        emit("update:loading", loading);
    },
);

/** `historyStore` histories for current user */
const historiesProxy = ref<HistorySummary[]>([]);
watch(
    () => histories.value as AnyHistory[],
    (h: AnyHistory[]) => {
        historiesProxy.value = h.filter((h) => userOwnsHistory(currentUser.value, h));
    },
    {
        immediate: true,
    },
);

const filtered = computed<HistorySummary[]>(() => {
    let filteredHistories: HistorySummary[] = [];
    if (!props.filter) {
        filteredHistories = historiesProxy.value;
    } else {
        const filters = HistoriesFilters.getFiltersForText(props.filter);
        filteredHistories = historiesProxy.value.filter((history: HistorySummary) => {
            if (!HistoriesFilters.testFilters(filters, history)) {
                return false;
            }
            return true;
        });
    }
    if (props.hideDeleted) {
        filteredHistories = filteredHistories.filter((h) => !h.deleted && !h.purged);
    }
    // Copy before sorting: with no filter this array is historiesProxy itself,
    // and sorting in place would mutate reactive state from inside a computed.
    return [...filteredHistories].sort((a, b) => {
        if (!isMultiviewPanel.value && a.id == currentHistoryId.value) {
            return -1;
        } else if (!isMultiviewPanel.value && b.id == currentHistoryId.value) {
            return 1;
        } else if (isMultiviewPanel.value && isPinned(a.id) && !isPinned(b.id)) {
            return -1;
        } else if (isMultiviewPanel.value && !isPinned(a.id) && isPinned(b.id)) {
            return 1;
        } else if (a.update_time < b.update_time) {
            return 1;
        } else {
            return -1;
        }
    });
});

/** is this the selector list for Multiview that shows up in the left panel */
const isMultiviewPanel = computed(() => !props.inModal && props.multiple);

function isActiveItem(history: HistorySummary) {
    if (isMultiviewPanel.value) {
        return isPinned(history.id);
    } else {
        return props.selectedHistories.some((item: PinnedHistory) => item.id == history.id);
    }
}

function isPinned(historyId: string) {
    return pinnedHistories.value.some((item: PinnedHistory) => item.id == historyId);
}

function historyClicked(history: HistorySummary) {
    emit("selectHistory", history);
    if (isMultiviewPanel.value) {
        if (isPinned(history.id)) {
            historyStore.unpinHistories([history.id]);
        } else {
            openInMulti(history);
        }
    }
}

const router = useRouter();

function setCurrentHistory(history: HistorySummary) {
    historyStore.setCurrentHistory(history.id);
    emit("update:show-modal", false);
}

function setCenterPanelHistory(history: HistorySummary) {
    router.push(`/histories/view?id=${history.id}`);
    emit("update:show-modal", false);
}

function setFilterValue(newFilter: string, newValue: string) {
    emit("setFilter", newFilter, newValue);
}

function openInMulti(history: HistorySummary) {
    router.push("/histories/view_multiple");
    historyStore.pinHistory(history.id);
    emit("update:show-modal", false);
}

/** Loads (paginates) for more histories
 * @param noScroll If true, we are not scrolling and will load _all_ items for current filter
 */
/** Reveals more of the list as it is scrolled.
 *
 * Searching no longer goes through here: the whole list is pulled in once and
 * matched locally, so there is no per-search request to supersede or cancel.
 */
async function loadMore() {
    if (busy.value) {
        return;
    }
    // Widen the rendered window first. The matches are already in memory, so
    // this costs nothing but the cards it adds.
    if (renderLimit.value < filtered.value.length) {
        renderLimit.value += RENDER_PAGE_SIZE;
        return;
    }
    if (props.filter || serverExhausted.value) {
        return;
    }
    busy.value = true;
    try {
        await historyStore.loadHistories(true);
    } finally {
        busy.value = false;
    }
}

function getHistoryBadges(history: HistorySummary) {
    return [
        {
            id: "items",
            label: `${history.count} items`,
            title: "Amount of items in history",
        },
    ];
}

function getHistorySecondaryActions(history: HistorySummary) {
    const actions: CardAction[] = [];
    if (props.additionalOptions.includes("set-current")) {
        actions.push({
            id: "set-current",
            label: "Set as current",
            icon: faSignInAlt,
            title: "Set this history as the current history",
            handler: () => setCurrentHistory(history),
        });
    }
    if (props.additionalOptions.includes("multi")) {
        actions.push({
            id: "multi",
            label: "Open in multi-view",
            icon: faColumns,
            title: "Open in multi-view",
            handler: () => openInMulti(history),
        });
    }
    if (props.additionalOptions.includes("center")) {
        actions.push({
            id: "center",
            label: "Open in center panel",
            icon: faListAlt,
            title: "Open in center panel",
            handler: () => setCenterPanelHistory(history),
        });
    }
    return actions;
}

function getHistoryTitleBadges(history: HistorySummary) {
    const badges: CardBadge[] = [];
    if (props.multiple && !isMultiviewPanel.value && history.id === currentHistoryId.value) {
        badges.push({
            id: "current",
            label: "Current",
            title: "This is the current history",
            variant: "primary",
        });
    }
    if (history.purged) {
        badges.push({
            id: "purged",
            label: "",
            title: "Permanently deleted",
            icon: faBurn,
            variant: "warning",
        });
    } else if (history.deleted) {
        badges.push({
            id: "deleted",
            label: "",
            title: "Deleted",
            icon: faTrash,
            variant: "danger",
        });
    }
    if (history.archived && userOwnsHistory(currentUser.value, history)) {
        badges.push({
            id: "archived",
            label: "",
            title: "Archived",
            icon: faArchive,
        });
    }
    if (props.multiple && !isMultiviewPanel.value && isPinned(history.id)) {
        badges.push({
            id: "pinned",
            label: isActiveItem(history) ? "currently pinned" : "will be unpinned",
            title: "This history is currently pinned in the multi-history view",
            variant: "info",
        });
    }
    return badges;
}
</script>

<template>
    <ScrollList
        :item-key="(history) => history.id"
        :in-panel="!props.inModal"
        :prop-items="visible"
        :prop-total-count="props.filter ? filtered.length : totalHistoryCount"
        :prop-busy="busy"
        name="history"
        name-plural="histories"
        @load-more="loadMore">
        <template v-slot:search>
            <BAlert v-if="!busy && hasNoResults" class="mb-2" variant="danger" show>No histories found.</BAlert>
        </template>

        <template v-slot:item="{ item: history }">
            <GCard
                :id="`history-${history.id}`"
                :data-pk="history.id"
                button
                :current="!(props.multiple && !isMultiviewPanel) && history.id === effectiveCurrentId"
                clickable
                :active="isActiveItem(history)"
                :selectable="props.multiple"
                :selected="isActiveItem(history)"
                :select-title="isMultiviewPanel ? 'Pin history' : 'Add/remove history from selection'"
                :badges="getHistoryBadges(history)"
                :secondary-actions="getHistorySecondaryActions(history)"
                :tags="history.tags"
                :max-visible-tags="isMultiviewPanel ? 1 : 10"
                :title="history.name"
                title-size="text"
                :title-badges="getHistoryTitleBadges(history)"
                :title-n-lines="2"
                :description="isMultiviewPanel ? undefined : history.annotation || undefined"
                :update-time="history.update_time"
                @select="historyClicked(history)"
                @tagClick="setFilterValue('tag', $event)"
                @title-click="historyClicked(history)"
                @click="() => historyClicked(history)" />
        </template>

        <template v-slot:footer-button-area>
            <slot name="footer-button-area"></slot>
        </template>
    </ScrollList>
</template>
