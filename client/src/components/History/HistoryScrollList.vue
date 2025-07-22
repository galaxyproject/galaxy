<script setup lang="ts">
import { faListAlt } from "@fortawesome/free-regular-svg-icons";
import { faArchive, faBurn, faColumns, faSignInAlt, faTrash } from "@fortawesome/free-solid-svg-icons";
import { BAlert, BBadge } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { type AnyHistory, type HistorySummary, userOwnsHistory } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import type { CardAction, CardBadge } from "../Common/GCard.types";
import { HistoriesFilters } from "./HistoriesFilters";

import GCard from "../Common/GCard.vue";
import ScrollList from "../ScrollList/ScrollList.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

type AdditionalOptions = "set-current" | "multi" | "center";
type PinnedHistory = { id: string };

interface Props {
    multiple?: boolean;
    selectedHistories?: PinnedHistory[];
    additionalOptions?: AdditionalOptions[];
    showModal?: boolean;
    inModal?: boolean;
    filter: string;
    loading: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    multiple: false,
    selectedHistories: () => [],
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
const { currentHistoryId, histories, totalHistoryCount, pinnedHistories } = storeToRefs(historyStore);
const { currentUser } = storeToRefs(useUserStore());

const hasNoResults = computed(() => props.filter && filtered.value.length == 0);
const validFilter = computed(() => props.filter && props.filter.length > 2);
const allLoaded = computed(() => totalHistoryCount.value <= filtered.value.length);

onMounted(async () => {
    // if mounted with a filter, load histories for filter
    if (props.filter !== "" && validFilter.value) {
        await loadMore(true);
    }
});

watch(
    () => props.filter,
    async (newVal: string, oldVal: string) => {
        if (newVal !== "" && validFilter.value && newVal !== oldVal) {
            await loadMore(true);
        }
    }
);

watch(
    () => busy.value,
    (loading: boolean) => {
        emit("update:loading", loading);
    }
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
    }
);

const filtered = computed<HistorySummary[]>(() => {
    let filteredHistories: HistorySummary[] = [];
    if (!validFilter.value) {
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
    return filteredHistories.sort((a, b) => {
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
async function loadMore(noScroll = false) {
    if (!busy.value && (noScroll || (!noScroll && !props.filter && !allLoaded.value))) {
        busy.value = true;
        const queryString = props.filter && HistoriesFilters.getQueryString(props.filter);
        await historyStore.loadHistories(true, queryString);
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
        :prop-items="filtered"
        :prop-total-count="totalHistoryCount"
        :prop-busy="busy"
        name="history"
        name-plural="histories"
        :load-disabled="Boolean(props.filter)"
        @load-more="loadMore">
        <template v-slot:search>
            <BBadge v-if="props.filter && !validFilter" class="alert-warning w-100 mb-2">
                Search term is too short
            </BBadge>
            <BAlert v-else-if="!busy && hasNoResults" class="mb-2" variant="danger" show>No histories found.</BAlert>
        </template>

        <template v-slot:item="{ item: history }">
            <!-- TODO: Long history names should be truncated, esp in multiview panel -->
            <GCard
                :id="`history-${history.id}`"
                :data-pk="history.id"
                button
                :current="!(props.multiple && !isMultiviewPanel) && history.id === currentHistoryId"
                clickable
                :active="isActiveItem(history)"
                :selectable="props.multiple"
                :selected="isActiveItem(history)"
                :select-title="isMultiviewPanel ? 'Pin history' : 'Add/remove history from selection'"
                :badges="getHistoryBadges(history)"
                :secondary-actions="getHistorySecondaryActions(history)"
                :title="history.name"
                title-size="text"
                :title-badges="getHistoryTitleBadges(history)"
                :update-time="history.update_time"
                @select="historyClicked(history)"
                @title-click="historyClicked(history)"
                @click="() => historyClicked(history)">
                <template v-slot:description>
                    <small v-if="!isMultiviewPanel && history.annotation" class="my-1">{{ history.annotation }}</small>

                    <StatelessTags
                        v-if="history.tags.length > 0"
                        class="my-1"
                        :value="history.tags"
                        :disabled="true"
                        :max-visible-tags="isMultiviewPanel ? 1 : 10"
                        @tag-click="setFilterValue('tag', $event)" />
                </template>
            </GCard>
        </template>

        <template v-slot:footer-button-area>
            <slot name="footer-button-area"></slot>
        </template>
    </ScrollList>
</template>
