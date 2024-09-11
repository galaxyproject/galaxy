<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheckSquare, faListAlt, faSquare } from "@fortawesome/free-regular-svg-icons";
import { faArrowDown, faColumns, faSignInAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useInfiniteScroll } from "@vueuse/core";
import { BAlert, BBadge, BButton, BButtonGroup, BListGroup, BListGroupItem, BOverlay } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { type AnyHistory, type HistorySummary, userOwnsHistory } from "@/api";
import { useAnimationFrameResizeObserver } from "@/composables/sensors/animationFrameResizeObserver";
import { useAnimationFrameScroll } from "@/composables/sensors/animationFrameScroll";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";

import { HistoriesFilters } from "./HistoriesFilters";

import TextSummary from "../Common/TextSummary.vue";
import HistoryIndicators from "./HistoryIndicators.vue";
import Heading from "@/components/Common/Heading.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import ScrollToTopButton from "@/components/ToolsList/ScrollToTopButton.vue";

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

library.add(faColumns, faSignInAlt, faListAlt, faArrowDown, faCheckSquare, faSquare);

const busy = ref(false);
const showAdvanced = ref(false);
const scrollableDiv = ref<HTMLElement | null>(null);

const historyStore = useHistoryStore();
const { currentHistoryId, histories, totalHistoryCount, pinnedHistories } = storeToRefs(historyStore);
const { currentUser } = storeToRefs(useUserStore());

const hasNoResults = computed(() => props.filter && filtered.value.length == 0);
const validFilter = computed(() => props.filter && props.filter.length > 2);
const allLoaded = computed(() => totalHistoryCount.value <= filtered.value.length);

// check if we have scrolled to the top or bottom of the scrollable div
const { arrived, scrollTop } = useAnimationFrameScroll(scrollableDiv);
const isScrollable = ref(false);
useAnimationFrameResizeObserver(scrollableDiv, ({ clientSize, scrollSize }) => {
    isScrollable.value = scrollSize.height >= clientSize.height + 1;
});
const scrolledTop = computed(() => !isScrollable.value || arrived.top);
const scrolledBottom = computed(() => !isScrollable.value || arrived.bottom);

onMounted(async () => {
    useInfiniteScroll(scrollableDiv.value, () => loadMore());
    // if mounted with a filter, load histories for filter
    if (props.filter !== "" && validFilter.value) {
        await loadMore(true);
    }
});

onUnmounted(() => {
    // Remove the infinite scrolling behavior
    useInfiniteScroll(scrollableDiv.value, () => {});
});

/** if screen size is as such that a scroller is not rendered,
 * we load enough histories so that a scroller is rendered
 */
watch(
    () => isScrollable.value,
    (scrollable: boolean) => {
        if (!scrollable && !allLoaded.value) {
            loadMore();
        }
    }
);

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

function scrollToTop() {
    scrollableDiv.value?.scrollTo({ top: 0, behavior: "smooth" });
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
</script>

<template>
    <div :class="isMultiviewPanel ? 'unified-panel' : 'flex-column-overflow'">
        <div class="unified-panel-controls">
            <BBadge v-if="props.filter && !validFilter" class="alert-warning w-100 mb-2">
                Search term is too short
            </BBadge>
            <BAlert v-else-if="!busy && hasNoResults" class="mb-2" variant="danger" show>No histories found.</BAlert>
        </div>

        <div
            class="scroll-list-container"
            :class="{
                'in-panel': isMultiviewPanel,
                'scrolled-top': scrolledTop,
                'scrolled-bottom': scrolledBottom,
            }">
            <div
                v-show="!showAdvanced"
                ref="scrollableDiv"
                :class="{
                    'scroll-list': !hasNoResults,
                    'in-panel': isMultiviewPanel,
                    'in-modal': props.inModal,
                    toolMenuContainer: isMultiviewPanel,
                }"
                role="list">
                <BListGroup>
                    <BListGroupItem
                        v-for="history in filtered"
                        :key="history.id"
                        :data-pk="history.id"
                        button
                        :class="{
                            current: history.id === currentHistoryId,
                            'panel-item': isMultiviewPanel,
                        }"
                        :active="isActiveItem(history)"
                        @click="() => historyClicked(history)">
                        <div class="overflow-auto w-100">
                            <div :class="!isMultiviewPanel ? 'd-flex justify-content-between align-items-center' : ''">
                                <div v-if="!isMultiviewPanel">
                                    <Heading h3 inline bold size="text">
                                        <span>{{ history.name }}</span>
                                        <i v-if="history.id === currentHistoryId">(Current)</i>
                                    </Heading>
                                    <i
                                        v-if="props.multiple && isPinned(history.id)"
                                        title="This history is currently pinned in the multi-history view">
                                        (currently pinned)
                                    </i>
                                </div>
                                <TextSummary v-else component="h4" :description="history.name" one-line-summary />
                                <HistoryIndicators :history="history" include-count />
                            </div>

                            <p v-if="!isMultiviewPanel && history.annotation" class="my-1">{{ history.annotation }}</p>

                            <StatelessTags
                                v-if="history.tags.length > 0"
                                class="my-1"
                                :value="history.tags"
                                :disabled="true"
                                :max-visible-tags="isMultiviewPanel ? 1 : 10"
                                @tag-click="setFilterValue('tag', $event)" />

                            <div
                                v-if="props.additionalOptions.length > 0"
                                class="d-flex justify-content-end align-items-center mt-1">
                                <BButtonGroup>
                                    <BButton
                                        v-if="
                                            props.additionalOptions.includes('set-current') &&
                                            currentHistoryId !== history.id
                                        "
                                        v-b-tooltip.noninteractive.hover
                                        :title="localize('Set as current history')"
                                        variant="link"
                                        class="p-0 px-1"
                                        @click.stop="() => setCurrentHistory(history)">
                                        <FontAwesomeIcon :icon="faSignInAlt" />
                                    </BButton>

                                    <BButton
                                        v-if="props.additionalOptions.includes('multi')"
                                        v-b-tooltip.noninteractive.hover
                                        :title="localize('Open in multi-view')"
                                        variant="link"
                                        class="p-0 px-1"
                                        @click.stop="() => openInMulti(history)">
                                        <FontAwesomeIcon :icon="faColumns" />
                                    </BButton>

                                    <BButton
                                        v-if="props.additionalOptions.includes('center')"
                                        v-b-tooltip.noninteractive.hover
                                        :title="localize('Open in center panel')"
                                        variant="link"
                                        class="p-0 px-1"
                                        @click.stop="() => setCenterPanelHistory(history)">
                                        <FontAwesomeIcon :icon="faListAlt" />
                                    </BButton>
                                </BButtonGroup>
                            </div>
                        </div>
                        <div v-if="isMultiviewPanel">
                            <FontAwesomeIcon v-if="isActiveItem(history)" :icon="faCheckSquare" size="lg" />
                            <FontAwesomeIcon v-else :icon="faSquare" size="lg" />
                        </div>
                    </BListGroupItem>
                    <div>
                        <div v-if="allLoaded || props.filter !== ''" class="list-end my-2">
                            <span v-if="filtered.length == 1">- {{ filtered.length }} history loaded -</span>
                            <span v-else-if="filtered.length > 1">- All {{ filtered.length }} histories loaded -</span>
                        </div>
                        <BOverlay :show="busy" opacity="0.5" />
                    </div>
                </BListGroup>
            </div>
            <ScrollToTopButton :offset="scrollTop" @click="scrollToTop" />
        </div>

        <div :class="!isMultiviewPanel && 'd-flex flex-row mt-3'">
            <div
                v-if="!allLoaded"
                class="mr-auto d-flex justify-content-center align-items-center"
                :class="isMultiviewPanel && 'mt-1'">
                <i class="mr-1">Loaded {{ filtered.length }} out of {{ totalHistoryCount }} histories</i>
                <BButton
                    v-if="!props.filter"
                    v-b-tooltip.noninteractive.hover
                    data-description="load more histories button"
                    size="sm"
                    :title="localize('Load More')"
                    variant="link"
                    @click="loadMore()">
                    <FontAwesomeIcon :icon="faArrowDown" />
                </BButton>
            </div>

            <div v-if="props.inModal" class="ml-auto">
                <slot name="modal-button-area"></slot>
            </div>
        </div>
    </div>
</template>
