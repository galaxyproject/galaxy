<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, type Ref, ref, set as VueSet, unref, watch } from "vue";

import { type HistoryItemSummary, type HistorySummaryExtended, userOwnsHistory } from "@/api";
import ExpandedItems from "@/components/History/Content/ExpandedItems";
import SelectedItems from "@/components/History/Content/SelectedItems";
import { HistoryFilters } from "@/components/History/HistoryFilters";
import { deleteContent, updateContentFields } from "@/components/History/model/queries";
import { useActiveElement } from "@/composables/useActiveElement";
import { startWatchingHistory } from "@/store/historyStore/model/watchHistory";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import { type Alias, getOperatorForAlias } from "@/utils/filtering";
import { setItemDragstart } from "@/utils/setDrag";

import { useHistoryDragDrop } from "../../../composables/historyDragDrop";

import HistoryCounter from "./HistoryCounter.vue";
import HistoryDetails from "./HistoryDetails.vue";
import HistoryDropZone from "./HistoryDropZone.vue";
import HistoryEmpty from "./HistoryEmpty.vue";
import HistoryMessages from "./HistoryMessages.vue";
import HistoryOperations from "./HistoryOperations/HistoryOperations.vue";
import OperationErrorDialog from "./HistoryOperations/OperationErrorDialog.vue";
import SelectionChangeWarning from "./HistoryOperations/SelectionChangeWarning.vue";
import HistorySelectionOperations from "./HistoryOperations/SelectionOperations.vue";
import HistorySelectionStatus from "./HistoryOperations/SelectionStatus.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";
import ContentItem from "@/components/History/Content/ContentItem.vue";
import ListingLayout from "@/components/History/Layout/ListingLayout.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface BackendFilterError {
    err_msg: string;
    err_code: number;
    column?: string;
    col?: string;
    operation?: Alias;
    op?: Alias;
    value?: string;
    val?: string;
    ValueError?: string;
}

interface Props {
    listOffset?: number;
    history: HistorySummaryExtended;
    filter?: string;
    filterable?: boolean;
    isMultiViewItem?: boolean;
}

type ContentItemRef = Record<string, Ref<InstanceType<typeof ContentItem> | null>>;

const props = withDefaults(defineProps<Props>(), {
    listOffset: 0,
    filter: "",
    filterable: false,
    isMultiViewItem: false,
});

const filterClass = HistoryFilters;
const filterText = ref("");
const invisibleHistoryItems = ref<Record<string, any>>({});
const isLoading = ref(false);
const offsetQueryParam = ref(0);
const searchError = ref<BackendFilterError | undefined>(undefined);
const showAdvanced = ref(false);
const operationRunning = ref<string | null>(null);
const operationError = ref(null);
const querySelectionBreak = ref(false);
const contentItemRefs = computed(() => {
    return historyItems.value.reduce((acc: ContentItemRef, item) => {
        acc[itemUniqueKey(item)] = ref(null);
        return acc;
    }, {});
});
const currItemFocused = useActiveElement();
const lastItemId = ref<string | null>(null);

const { currentFilterText, currentHistoryId } = storeToRefs(useHistoryStore());
const { lastCheckedTime, totalMatchesCount, isWatching } = storeToRefs(useHistoryItemsStore());

const historyStore = useHistoryStore();
const historyItemsStore = useHistoryItemsStore();
const { currentUser } = storeToRefs(useUserStore());

const historyIdComputed = computed(() => props.history.id);
const { showDropZone, onDragEnter, onDragLeave, onDragOver, onDrop } = useHistoryDragDrop(historyIdComputed);

const currentUserOwnsHistory = computed(() => {
    return userOwnsHistory(currentUser.value, props.history);
});
const canEditHistory = computed(() => {
    return currentUserOwnsHistory.value && !props.history.deleted && !props.history.archived;
});

const historyUpdateTime = computed(() => {
    return props.history.update_time;
});

const queryKey = computed(() => {
    return `${props.history.id}-${filterText.value}`;
});

const queryDefault = computed(() => {
    return !filterText.value;
});

const isProcessing = computed(() => {
    if (!operationRunning.value) {
        return false;
    }
    return operationRunning?.value >= props.history.update_time;
});

const historyItems = computed(() => {
    return historyItemsStore.getHistoryItems(props.history.id, filterText.value);
});

const visibleHistoryItems = computed(() => {
    return historyItems.value.filter((item) => !invisibleHistoryItems.value[item.hid]);
});

const formattedSearchError = computed(() => {
    const newError = unref(searchError);
    if (!newError) {
        return null;
    }

    const { column, col, operation, op, value, val, err_msg, ValueError } = newError;
    const alias = operation || op;
    const operator = alias ? getOperatorForAlias(alias) : ":";

    return {
        filter: `${column || col}${operator}`,
        value: value || val,
        msg: err_msg,
        typeError: ValueError,
    };
});

const storeFilterText = computed(() => {
    if (props.history.id !== currentHistoryId.value) {
        return "";
    }
    return currentFilterText.value || "";
});

const lastItemFocused = computed(() => {
    return lastItemId.value ? historyItems.value.find((item) => lastItemId.value === `dataset-${item.id}`) : null;
});

watch(offsetQueryParam, () => loadHistoryItems());

watch(
    () => queryKey.value,
    () => {
        invisibleHistoryItems.value = {};
        offsetQueryParam.value = 0;
        loadHistoryItems();
        lastItemId.value = null;
    }
);

watch(
    () => props.filter,
    (newVal) => (filterText.value = newVal)
);

watch(filterText, (newFilterTextValue) => {
    if (props.filterable) {
        historyStore.setFilterText(props.history.id, newFilterTextValue);
    }
});

watch(storeFilterText, (newFilterTextValue) => {
    if (props.filterable) {
        filterText.value = newFilterTextValue;
    }
});

watch(historyUpdateTime, async () => await loadHistoryItems());

watch(
    () => props.history.id,
    (newValue, currentValue) => {
        if (newValue !== currentValue) {
            operationRunning.value = null;
            lastItemId.value = null;
        }
    }
);

watch(historyItems, (newHistoryItems) => {
    if (!invisibleHistoryItems.value) {
        return;
    }

    // Re-hide invisible history items when `historyItems` changes
    for (const newHistoryItem of newHistoryItems) {
        if (invisibleHistoryItems.value[newHistoryItem.hid]) {
            VueSet(invisibleHistoryItems.value, newHistoryItem.hid, false);
        }
    }
});

watch(
    () => currItemFocused.value,
    (newItem, oldItem) => {
        // if user clicked elsewhere, set lastItemId to the last focused item
        // (if it was indeed a history .content-item)
        if (newItem && oldItem?.classList?.contains("content-item") && oldItem?.getAttribute("data-hid")) {
            lastItemId.value = oldItem?.id || null;
        }
    }
);

function getHighlight(item: HistoryItemSummary) {
    if (unref(isLoading)) {
        return undefined;
    }

    const highlightsKey = parseInt(filterClass.getFilterValue(unref(filterText), "related"));
    if (!highlightsKey) {
        return undefined;
    }

    if (highlightsKey === item.hid) {
        return "active";
    }

    if (item.hid > highlightsKey) {
        return "output";
    }

    return "input";
}

function hasMatches(items: HistoryItemSummary[]) {
    return !!items && items.length > 0;
}

function isDataset(item: HistoryItemSummary) {
    return item.history_content_type === "dataset";
}

async function loadHistoryItems() {
    isLoading.value = true;
    try {
        await historyItemsStore.fetchHistoryItems(props.history.id, filterText.value, offsetQueryParam.value);
        searchError.value = undefined;
    } catch (error: any) {
        if (error.response && error.response.data && error.response.data.err_msg) {
            console.debug("HistoryPanel - Load items error:", error.response.data.err_msg);
            searchError.value = error.response.data;
        } else {
            console.debug("HistoryPanel - Load items error.", error);
        }
    } finally {
        isLoading.value = false;
    }
}

async function onDelete(item: HistoryItemSummary, recursive = false) {
    isLoading.value = true;
    setInvisible(item);

    try {
        await deleteContent(item, { recursive: recursive });
        updateContentStats();
    } finally {
        isLoading.value = false;
    }
}

function onHideSelection(selectedItems: HistoryItemSummary[]) {
    for (const item of selectedItems) {
        setInvisible(item);
    }
}

function onScroll(newOffset: number) {
    offsetQueryParam.value = newOffset;
}

async function onUndelete(item: HistoryItemSummary) {
    setInvisible(item);
    isLoading.value = true;

    try {
        await updateContentFields(item, { deleted: false });
        updateContentStats();
    } finally {
        isLoading.value = false;
    }
}

async function onUnhide(item: HistoryItemSummary) {
    setInvisible(item);
    isLoading.value = true;

    try {
        await updateContentFields(item, { visible: true });
        updateContentStats();
    } finally {
        isLoading.value = false;
    }
}

function updateContentStats() {
    historyStore.updateContentStats(props.history.id);
}

function reloadContents() {
    startWatchingHistory();
}

function setInvisible(item: HistoryItemSummary) {
    VueSet(unref(invisibleHistoryItems), item.hid, true);
}

function onTagChange(item: HistoryItemSummary, newTags: string[]) {
    item.tags = newTags;
}

function onOperationError(error: any) {
    console.debug("HistoryPanel - Operation error.", error);
    operationError.value = error;
}

function updateFilterValue(filterKey: string, newValue: any) {
    const currentFilterText = filterText.value;
    filterText.value = filterClass.setFilterValue(currentFilterText, filterKey, newValue);
}

function getItemKey(item: HistoryItemSummary) {
    return itemUniqueKey(item);
}

function itemUniqueKey(item: HistoryItemSummary) {
    return `${item.history_content_type}-${item.id}`;
}

onMounted(async () => {
    // `filterable` here indicates if this is the current history panel
    if (props.filterable && !props.filter) {
        filterText.value = storeFilterText.value;
    }
    await loadHistoryItems();
    // if there is a listOffset, we are coming from a collection view, so focus on item at that offset
    if (props.listOffset) {
        const itemAtOffset = historyItems.value[props.listOffset];
        if (itemAtOffset) {
            const itemElement = contentItemRefs.value[itemUniqueKey(itemAtOffset)]?.value?.$el as HTMLElement;
            itemElement?.focus();
        }
    }
});

function arrowNavigate(item: HistoryItemSummary, eventKey: string) {
    let nextItem = null;
    if (eventKey === "ArrowDown") {
        nextItem = historyItems.value[historyItems.value.indexOf(item) + 1];
    } else if (eventKey === "ArrowUp") {
        nextItem = historyItems.value[historyItems.value.indexOf(item) - 1];
    }
    if (nextItem) {
        const itemElement = contentItemRefs.value[itemUniqueKey(nextItem)]?.value?.$el as HTMLElement;
        itemElement?.focus();
    }
    return nextItem;
}
</script>

<template>
    <ExpandedItems
        v-slot="{ expandedCount, isExpanded, setExpanded, collapseAll }"
        :scope-key="props.history.id"
        :get-item-key="getItemKey">
        <SelectedItems
            v-slot="{
                selectedItems,
                showSelection,
                isQuerySelection,
                selectionSize,
                setShowSelection,
                selectAllInCurrentQuery,
                isSelected,
                rangeSelect,
                setSelected,
                shiftArrowKeySelect,
                initKeySelection,
                resetSelection,
                initSelectedItem,
            }"
            :scope-key="queryKey"
            :get-item-key="getItemKey"
            :filter-text="filterText"
            :all-items="historyItems"
            :total-items-in-query="totalMatchesCount"
            @query-selection-break="querySelectionBreak = true">
            <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
            <section
                class="history-layout d-flex flex-column w-100 h-100"
                @drop.prevent="onDrop"
                @dragenter.prevent="onDragEnter"
                @dragover="onDragOver"
                @dragleave.prevent="onDragLeave">
                <slot name="navigation" :history="history" />

                <FilterMenu
                    v-if="filterable"
                    :key="props.history.id"
                    class="content-operations-filters mx-3"
                    name="History Items"
                    placeholder="search datasets"
                    :filter-class="filterClass"
                    :filter-text.sync="filterText"
                    :loading="isLoading"
                    :search-error="searchError"
                    :show-advanced.sync="showAdvanced" />

                <section v-if="!showAdvanced">
                    <HistoryDetails
                        :history="history"
                        :writeable="canEditHistory"
                        :summarized="isMultiViewItem"
                        @update:history="historyStore.updateHistory($event)" />

                    <HistoryMessages :history="history" :current-user="currentUser" />

                    <HistoryCounter
                        :history="history"
                        :is-watching="isWatching"
                        :last-checked="lastCheckedTime"
                        :show-controls="canEditHistory"
                        :owned-by-current-user="userOwnsHistory(currentUser, history)"
                        :filter-text.sync="filterText"
                        :hide-reload="isMultiViewItem"
                        @reloadContents="reloadContents" />

                    <HistoryOperations
                        v-if="canEditHistory"
                        :history="history"
                        :is-multi-view-item="isMultiViewItem"
                        :show-selection="showSelection"
                        :expanded-count="expandedCount"
                        :has-matches="hasMatches(historyItems)"
                        :operation-running.sync="operationRunning"
                        @update:show-selection="setShowSelection"
                        @collapse-all="collapseAll">
                        <template v-slot:selection-operations>
                            <HistorySelectionOperations
                                :history="history"
                                :is-multi-view-item="isMultiViewItem"
                                :filter-text="filterText"
                                :content-selection="selectedItems"
                                :selection-size="selectionSize"
                                :is-query-selection="isQuerySelection"
                                :total-items-in-query="totalMatchesCount"
                                :operation-running.sync="operationRunning"
                                @update:show-selection="setShowSelection"
                                @operation-error="onOperationError"
                                @hide-selection="onHideSelection"
                                @reset-selection="resetSelection" />

                            <HistorySelectionStatus
                                v-if="showSelection"
                                :selection-size="selectionSize"
                                @select-all="selectAllInCurrentQuery()"
                                @reset-selection="resetSelection" />
                        </template>
                    </HistoryOperations>

                    <SelectionChangeWarning v-if="!isMultiViewItem" :query-selection-break="querySelectionBreak" />

                    <OperationErrorDialog
                        v-if="operationError"
                        :operation-error="operationError"
                        @hide="operationError = null" />
                </section>

                <section v-show="!showAdvanced" class="position-relative flex-grow-1 scroller overflow-hidden">
                    <HistoryDropZone v-if="showDropZone" />
                    <div class="h-100">
                        <div v-if="isLoading && historyItems && historyItems.length === 0">
                            <BAlert class="m-2" variant="info" show>
                                <LoadingSpan message="Loading History" />
                            </BAlert>
                        </div>
                        <BAlert v-else-if="isProcessing" class="m-2" variant="info" show>
                            <LoadingSpan message="Processing operation" />
                        </BAlert>
                        <div v-else-if="historyItems.length === 0">
                            <HistoryEmpty v-if="queryDefault" :writable="canEditHistory" class="m-2" />

                            <BAlert v-else-if="formattedSearchError" class="m-2" variant="danger" show>
                                Error in filter:
                                <a href="javascript:void(0)" @click="showAdvanced = true">
                                    {{ formattedSearchError.filter }}'{{ formattedSearchError.value }}'
                                </a>
                            </BAlert>
                            <BAlert v-else class="m-2" variant="info" show> No data found for selected filter. </BAlert>
                        </div>
                        <ListingLayout
                            v-else
                            :offset="listOffset"
                            :items="visibleHistoryItems"
                            :query-key="queryKey"
                            data-key="hid"
                            @scroll="onScroll">
                            <template v-slot:item="{ item, currentOffset }">
                                <ContentItem
                                    :id="item.hid"
                                    :ref="contentItemRefs[itemUniqueKey(item)]"
                                    is-history-item
                                    :item="item"
                                    :name="item.name"
                                    :writable="canEditHistory"
                                    :expand-dataset="isExpanded(item)"
                                    :is-dataset="isDataset(item)"
                                    :is-range-select-anchor="
                                        initSelectedItem && itemUniqueKey(item) === itemUniqueKey(initSelectedItem)
                                    "
                                    :highlight="getHighlight(item)"
                                    :selected="isSelected(item)"
                                    :selectable="showSelection"
                                    :filterable="filterable"
                                    @arrow-navigate="arrowNavigate(item, $event)"
                                    @drag-start="
                                        setItemDragstart(
                                            item,
                                            $event,
                                            showSelection && isSelected(item),
                                            selectionSize,
                                            selectedItems
                                        )
                                    "
                                    @hide-selection="setShowSelection(false)"
                                    @init-key-selection="initKeySelection"
                                    @shift-arrow-select="
                                        (eventKey) => shiftArrowKeySelect(item, arrowNavigate(item, eventKey), eventKey)
                                    "
                                    @select-all="selectAllInCurrentQuery(false)"
                                    @selected-to="rangeSelect(item, lastItemFocused)"
                                    @tag-click="updateFilterValue('tag', $event)"
                                    @tag-change="onTagChange"
                                    @toggleHighlights="updateFilterValue('related', item.hid)"
                                    @update:expand-dataset="setExpanded(item, $event)"
                                    @update:selected="setSelected(item, $event)"
                                    @view-collection="$emit('view-collection', item, currentOffset)"
                                    @delete="onDelete"
                                    @undelete="onUndelete(item)"
                                    @unhide="onUnhide(item)">
                                    <template v-slot:sub_items="slotProps">
                                        <div v-if="slotProps.subItemsVisible" class="pl-2 sub-items-content">
                                            <ContentItem
                                                v-for="subItem in item.sub_items"
                                                :id="subItem.hid"
                                                :key="subItem.id"
                                                :item="subItem"
                                                :name="subItem.name"
                                                :expand-dataset="isExpanded(subItem)"
                                                :is-dataset="isDataset(subItem)"
                                                :is-sub-item="true"
                                                @update:expand-dataset="setExpanded(subItem, $event)" />
                                        </div>
                                    </template>
                                </ContentItem>
                            </template>
                        </ListingLayout>
                    </div>
                </section>
            </section>
        </SelectedItems>
    </ExpandedItems>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.sub-items-content {
    background: $body-bg;
}
</style>
