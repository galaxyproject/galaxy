<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faListAlt } from "@fortawesome/free-regular-svg-icons";
import { faArrowDown, faCheckSquare, faColumns, faSignInAlt, faSquare } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useInfiniteScroll } from "@vueuse/core";
import { BBadge, BButton, BButtonGroup, BListGroup, BListGroupItem } from "bootstrap-vue";
import { orderBy } from "lodash";
import isEqual from "lodash.isequal";
import { storeToRefs } from "pinia";
import { computed, onMounted, onUnmounted, type PropType, type Ref, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import type { HistoryDetailed, HistorySummary } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";

import { HistoriesFilters } from "./HistoriesFilters";

import TextSummary from "../Common/TextSummary.vue";
import Heading from "@/components/Common/Heading.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import UtcDate from "@/components/UtcDate.vue";

type AdditionalOptions = "set-current" | "multi" | "center";

const props = defineProps({
    multiple: { type: Boolean, default: false },
    histories: { type: Array as PropType<HistorySummary[]>, default: () => [] },
    additionalOptions: { type: Array as PropType<AdditionalOptions[]>, default: () => [] },
    showModal: { type: Boolean, default: false },
    inModal: { type: Boolean, default: false },
    filter: { type: String, default: "" },
    loading: { type: Boolean, default: false },
});

const emit = defineEmits<{
    (e: "selectHistory", history: HistorySummary): void;
    (e: "selectHistories", histories: { id: string }[]): void;
    (e: "setFilter", filter: string, value: string): void;
    (e: "update:loading", loading: boolean): void;
}>();

library.add(faColumns, faSignInAlt, faListAlt, faArrowDown, faCheckSquare, faSquare);

const selectedHistories: Ref<{ id: string }[]> = ref([]);
const busy = ref(false);
const showAdvanced = ref(false);
const scrollableDiv: Ref<HTMLElement | null> = ref(null);

const historyStore = useHistoryStore();
const { currentHistoryId, totalHistoryCount, pinnedHistories } = storeToRefs(useHistoryStore());
const { currentUser } = storeToRefs(useUserStore());

const hasNoResults = computed(() => props.filter && filtered.value.length == 0);
const validFilter = computed(() => props.filter && props.filter.length > 2);
const allLoaded = computed(() => totalHistoryCount.value <= filtered.value.length);

onMounted(async () => {
    useInfiniteScroll(scrollableDiv.value, () => loadMore());
    if (props.filter !== "" && validFilter.value) {
        await loadMore(true);
    }
});

// retain previously selected histories when you reopen the modal in multi view
watch(
    () => props.showModal,
    (show: boolean) => {
        if (props.multiple && show) {
            selectedHistories.value = [...pinnedHistories.value];
        }
    },
    {
        immediate: true,
    }
);

onUnmounted(() => {
    // Remove the infinite scrolling behavior
    useInfiniteScroll(scrollableDiv.value, () => {});
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

// reactive proxy for props.histories, as the prop is not
// always guaranteed to be reactive for some strange reason.
// TODO: Re investigate when upgrading to vue3
/** `historyStore` histories for current user */
const historiesProxy: Ref<HistorySummary[]> = ref([]);
watch(
    () => props.histories as HistoryDetailed[],
    (h: HistoryDetailed[]) => {
        historiesProxy.value = h.filter(
            (h) => !h.user_id || (!currentUser.value?.isAnonymous && h.user_id === currentUser.value?.id)
        );
    },
    {
        immediate: true,
    }
);

const filtered: Ref<HistorySummary[]> = computed(() => {
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
        } else if (a.update_time < b.update_time) {
            return 1;
        } else {
            return -1;
        }
    });
});

/** this is the selector list that shows up in the left panel */
const isMultiviewPanel = computed(() => !props.inModal && props.multiple);

/** if pinned histories and selected histories are equal */
const pinnedSelectedEqual = computed(() => {
    // uses `orderBy` to ensure same ids are found in both `{ id: string }[]` arrays
    return isEqual(orderBy(pinnedHistories.value, ["id"], ["asc"]), orderBy(selectedHistories.value, ["id"], ["asc"]));
});

function isActiveItem(history: HistorySummary) {
    if (isMultiviewPanel.value) {
        return pinnedHistories.value.some((item) => item.id == history.id);
    } else {
        return selectedHistories.value.some((item) => item.id == history.id);
    }
}

function historyClicked(history: HistorySummary) {
    if (props.multiple && props.inModal) {
        const index = selectedHistories.value.findIndex((item) => item.id == history.id);
        if (index !== -1) {
            selectedHistories.value.splice(index, 1);
        } else {
            selectedHistories.value.push({ id: history.id });
        }
    } else if (isMultiviewPanel.value) {
        if (pinnedHistories.value.some((item) => item.id == history.id)) {
            historyStore.unpinHistories([history.id]);
        } else {
            openInMulti(history);
        }
    } else {
        emit("selectHistory", history);
        // modal.value?.hide();
    }
}

function selectHistories() {
    // set value of pinned histories in store
    emit("selectHistories", selectedHistories.value);
    // set local value equal to updated value from store
    selectedHistories.value = pinnedHistories.value;
    // modal.value?.hide();
}

const router = useRouter();

function setCurrentHistory(history: HistorySummary) {
    historyStore.setCurrentHistory(history.id);
    // modal.value?.hide();
}

function setCenterPanelHistory(history: HistorySummary) {
    router.push(`/histories/view?id=${history.id}`);
    // modal.value?.hide();
}

function setFilterValue(newFilter: string, newValue: string) {
    emit("setFilter", newFilter, newValue);
}

function openInMulti(history: HistorySummary) {
    router.push("/histories/view_multiple");
    historyStore.pinHistory(history.id);
    // modal.value?.hide();
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
    <div class="unified-panel">
        <div class="unified-panel-controls">
            <BBadge v-if="props.filter && !validFilter" class="alert-danger w-100 mb-2">
                Search string too short!
            </BBadge>
            <b-alert v-else-if="!busy && hasNoResults" class="mb-2" variant="danger" show>No histories found.</b-alert>
        </div>

        <div class="position-relative flex-grow-1">
            <div
                v-show="!showAdvanced"
                ref="scrollableDiv"
                :class="{ 'history-scroll-list': !hasNoResults, toolMenuContainer: isMultiviewPanel }"
                role="list">
                <BListGroup>
                    <BListGroupItem
                        v-for="history in filtered"
                        :key="history.id"
                        :data-pk="history.id"
                        button
                        :class="{
                            current: !isMultiviewPanel && history.id === currentHistoryId,
                            'panel-item': isMultiviewPanel,
                        }"
                        :active="isActiveItem(history)"
                        @click="() => historyClicked(history)">
                        <div class="overflow-auto">
                            <div :class="!isMultiviewPanel ? 'd-flex justify-content-between align-items-center' : ''">
                                <div v-if="!isMultiviewPanel">
                                    <Heading h3 inline bold size="text">
                                        <span>{{ history.name }}</span>
                                        <i v-if="history.id === currentHistoryId">(Current)</i>
                                    </Heading>
                                    <i
                                        v-if="props.multiple && pinnedHistories.some((h) => h.id === history.id)"
                                        v-b-tooltip.noninteractive.hover
                                        title="This history is currently pinned in the multi-history view">
                                        (currently pinned)
                                    </i>
                                </div>
                                <TextSummary v-else component="h4" :description="history.name" one-line-summary />
                                <div class="d-flex align-items-center flex-gapx-1">
                                    <BBadge
                                        v-b-tooltip.noninteractive.hover
                                        pill
                                        :title="localize('Amount of items in history')">
                                        {{ history.count }} {{ localize("items") }}
                                    </BBadge>
                                    <BBadge
                                        v-if="history.update_time"
                                        v-b-tooltip.noninteractive.hover
                                        pill
                                        :title="localize('Last edited')">
                                        <UtcDate :date="history.update_time" mode="elapsed" />
                                    </BBadge>
                                </div>
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
                                        v-if="props.additionalOptions.includes('set-current')"
                                        v-b-tooltip.noninteractive.hover
                                        :title="localize('Set as current history')"
                                        variant="link"
                                        class="p-0 px-1"
                                        @click.stop="() => setCurrentHistory(history)">
                                        <FontAwesomeIcon icon="fa-sign-in-alt" />
                                    </BButton>

                                    <BButton
                                        v-if="props.additionalOptions.includes('multi')"
                                        v-b-tooltip.noninteractive.hover
                                        :title="localize('Open in multi-view')"
                                        variant="link"
                                        class="p-0 px-1"
                                        @click.stop="() => openInMulti(history)">
                                        <FontAwesomeIcon icon="fa-columns" />
                                    </BButton>

                                    <BButton
                                        v-if="props.additionalOptions.includes('center')"
                                        v-b-tooltip.noninteractive.hover
                                        :title="localize('Open in center panel')"
                                        variant="link"
                                        class="p-0 px-1"
                                        @click.stop="() => setCenterPanelHistory(history)">
                                        <FontAwesomeIcon icon="far fa-list-alt" />
                                    </BButton>
                                </BButtonGroup>
                            </div>
                        </div>
                        <div v-if="isMultiviewPanel" class="d-flex align-items-center">
                            <FontAwesomeIcon v-if="isActiveItem(history)" :icon="['far', 'check-square']" size="lg" />
                            <FontAwesomeIcon v-else :icon="['far', 'square']" size="lg" />
                        </div>
                    </BListGroupItem>
                    <div>
                        <div v-if="allLoaded || props.filter !== ''" class="list-end my-2">
                            <span v-if="filtered.length == 1">- {{ filtered.length }} history loaded -</span>
                            <span v-else-if="filtered.length > 1">- All {{ filtered.length }} histories loaded -</span>
                        </div>
                        <b-overlay :show="busy" opacity="0.5" />
                    </div>
                </BListGroup>
            </div>
        </div>

        <!-- TODO: This stuff goes in the BModal footer -->
        <div>
            <div
                v-if="!allLoaded"
                class="mr-auto"
                :class="isMultiviewPanel && 'mt-1 d-flex justify-content-center align-items-center'">
                <i>Loaded {{ filtered.length }} out of {{ totalHistoryCount }} histories</i>
                <BButton
                    v-if="!props.filter"
                    v-b-tooltip.noninteractive.hover
                    class="load-more-hist-button"
                    size="sm"
                    title="Load More"
                    variant="link"
                    @click="loadMore()">
                    <FontAwesomeIcon icon="fa-arrow-down" />
                </BButton>
            </div>

            <div v-if="props.inModal">
                <i v-if="multiple">{{ selectedHistories.length }} histories selected</i>
                <BButton
                    v-if="multiple"
                    v-localize
                    :disabled="pinnedSelectedEqual || showAdvanced"
                    variant="primary"
                    @click="selectHistories">
                    Change Selected
                </BButton>
                <span v-else v-localize> Click a history to switch to it </span>
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.history-scroll-list {
    overflow-x: hidden;
    overflow-y: scroll;
    scroll-behavior: smooth;
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    // max-height: 65vh; /** TODO: should only apply to modal */
    .list-group {
        .list-group-item {
            border-radius: 0;

            &.panel-item {
                display: flex;
                justify-content: space-between;
                &:not(&.active) {
                    background: $panel-bg-color;
                }
            }

            &:not(&.panel-item) {
                &.current {
                    border-left: 0.25rem solid $brand-primary;
                }

                &:first-child {
                    border-top-left-radius: inherit;
                    border-top-right-radius: inherit;
                }

                &:last-child {
                    border-bottom-left-radius: inherit;
                    border-bottom-right-radius: inherit;
                }
            }
        }
    }
    .list-end {
        width: 100%;
        text-align: center;
        color: $text-light;
    }
}
</style>
