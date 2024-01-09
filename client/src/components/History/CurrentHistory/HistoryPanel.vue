<script setup lang="ts">
import { storeToRefs } from "pinia";
import { GetComponentPropTypes } from "types/utilityTypes";
import { computed, onMounted, PropType, ref, set as VueSet, unref, watch } from "vue";

import { copyDataset } from "@/api/datasets";
import ExpandedItems from "@/components/History/Content/ExpandedItems";
import SelectedItems from "@/components/History/Content/SelectedItems";
import { HistoryFilters } from "@/components/History/HistoryFilters";
import { deleteContent, updateContentFields } from "@/components/History/model/queries";
import { Toast } from "@/composables/toast";
import { startWatchingHistory } from "@/store/historyStore/model/watchHistory";
import { type HistoryItem, useHistoryItemsStore } from "@/stores/historyItemsStore";
import { useHistoryStore } from "@/stores/historyStore";
import { type Alias, getOperatorForAlias } from "@/utils/filtering";

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

const props = defineProps({
    listOffset: {
        type: Number,
        default: 0,
    },
    history: {
        type: Object as PropType<Record<string, any> & GetComponentPropTypes<typeof HistoryCounter>["history"]>,
        required: true,
    },
    filter: {
        type: String,
        default: "",
    },
    canEditHistory: {
        type: Boolean,
        default: true,
    },
    shouldShowControls: {
        type: Boolean,
        default: true,
    },
    filterable: {
        type: Boolean,
        default: false,
    },
    isMultiViewItem: {
        type: Boolean,
        default: false
    },
});

const filterClass = HistoryFilters;
const filterText = ref("");
const invisibleHistoryItems = ref<Record<string, any>>({});
const isLoading = ref(false);
const offsetQueryParam = ref(0);
const searchError = ref<BackendFilterError | undefined>(undefined);
const showAdvanced = ref(false);
const showDropZone = ref(false);
const operationRunning = ref(null);
const operationError = ref(null);
const querySelectionBreak = ref(false);
const dragTarget = ref<EventTarget | null>(null);

const { currentFilterText, currentHistoryId } = storeToRefs(useHistoryStore());
const { lastCheckedTime, totalMatchesCount, isWatching } = storeToRefs(useHistoryItemsStore());

const historyStore = useHistoryStore();
const historyItemsStore = useHistoryItemsStore();

const historyUpdateTime = computed(() => {
    return props.history.update_time as Date;
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

watch(offsetQueryParam, () => loadHistoryItems());

watch(
    () => queryKey.value,
    () => {
        invisibleHistoryItems.value = {};
        offsetQueryParam.value = 0;
        loadHistoryItems();
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

function getHighlight(item: HistoryItem) {
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

function hasMatches(items: HistoryItem[]) {
    return !!items && items.length > 0;
}

function isDataset(item: HistoryItem) {
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

async function onDelete(item: HistoryItem, recursive = false) {
    isLoading.value = true;
    setInvisible(item);

    try {
        await deleteContent(item, { recursive: recursive });
    } finally {
        isLoading.value = false;
    }
}

function onHideSelection(selectedItems: HistoryItem[]) {
    for (const item of selectedItems) {
        setInvisible(item);
    }
}

function onScroll(newOffset: number) {
    offsetQueryParam.value = newOffset;
}

async function onUndelete(item: HistoryItem) {
    setInvisible(item);
    isLoading.value = true;

    try {
        await updateContentFields(item, { deleted: false });
    } finally {
        isLoading.value = false;
    }
}

async function onUnhide(item: HistoryItem) {
    setInvisible(item);
    isLoading.value = true;

    try {
        await updateContentFields(item, { visible: true });
    } finally {
        isLoading.value = false;
    }
}

function reloadContents() {
    startWatchingHistory();
}

function setInvisible(item: HistoryItem) {
    VueSet(unref(invisibleHistoryItems), item.hid, true);
}

function onTagChange(item: HistoryItem, newTags: string[]) {
    item.tags = newTags;
}

function onOperationError(error: any) {
    console.debug("HistoryPanel - Operation error.", error);
    operationError.value = error;
}

function onDragEnter(e: DragEvent) {
    dragTarget.value = e.target;
    showDropZone.value = true;
}

function onDragLeave(e: DragEvent) {
    if (dragTarget.value === e.target) {
        showDropZone.value = false;
    }
}

async function onDrop(evt: any) {
    showDropZone.value = false;
    let data;
    try {
        data = JSON.parse(evt.dataTransfer.getData("text"))[0];
    } catch (error) {
        // this was not a valid object for this dropzone, ignore
    }

    if (!data || data.history_id === props.history.id) {
        return;
    }

    try {
        const dataSource = data.history_content_type === "dataset" ? "hda" : "hdca";
        await copyDataset(data.id, props.history.id, data.history_content_type, dataSource);

        if (data.history_content_type === "dataset") {
            Toast.info("Dataset copied to history");
        } else {
            Toast.info("Collection copied to history");
        }

        historyStore.loadHistoryById(props.history.id);
    } catch (error) {
        Toast.error(`${error}`);
    }
}

function updateFilterValue(newFilterText: string, newValue: any) {
    const currentFilterText = filterText.value;
    filterText.value = filterClass.setFilterValue(currentFilterText, newFilterText, newValue);
}

function getItemKey(item: HistoryItem) {
    return item.type_id;
}

onMounted(async () => {
    // `filterable` here indicates if this is the current history panel
    if (props.filterable && !props.filter) {
        filterText.value = storeFilterText.value;
    }
    await loadHistoryItems();
});
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
                setSelected,
                resetSelection,
            }"
            :scope-key="queryKey"
            :get-item-key="getItemKey"
            :filter-text="filterText"
            :total-items-in-query="totalMatchesCount"
            @query-selection-break="querySelectionBreak = true">
            <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
            <section
                class="history-layout d-flex flex-column w-100"
                @drop.prevent="onDrop"
                @dragenter.prevent="onDragEnter"
                @dragover.prevent
                @dragleave.prevent="onDragLeave">
                <slot name="navigation" :history="history" />

                <FilterMenu
                    v-if="filterable"
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

                    <HistoryMessages :history="history" />

                    <HistoryCounter
                        :history="history"
                        :is-watching="isWatching"
                        :last-checked="lastCheckedTime"
                        :show-controls="shouldShowControls"
                        :filter-text.sync="filterText"
                        @reloadContents="reloadContents" />

                    <HistoryOperations
                        v-if="shouldShowControls"
                        :history="history"
                        :show-selection="showSelection"
                        :expanded-count="expandedCount"
                        :has-matches="hasMatches(historyItems)"
                        :operation-running.sync="operationRunning"
                        @update:show-selection="setShowSelection"
                        @collapse-all="collapseAll">
                        <template v-slot:selection-operations>
                            <HistorySelectionOperations
                                :history="history"
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
                                @select-all="selectAllInCurrentQuery(historyItems)"
                                @reset-selection="resetSelection" />
                        </template>
                    </HistoryOperations>

                    <SelectionChangeWarning :query-selection-break="querySelectionBreak" />

                    <OperationErrorDialog
                        v-if="operationError"
                        :operation-error="operationError"
                        @hide="operationError = null" />
                </section>

                <section v-if="!showAdvanced" class="position-relative flex-grow-1 scroller">
                    <HistoryDropZone v-if="showDropZone" />
                    <div>
                        <div v-if="isLoading && historyItems && historyItems.length === 0">
                            <b-alert class="m-2" variant="info" show>
                                <LoadingSpan message="Loading History" />
                            </b-alert>
                        </div>
                        <b-alert v-else-if="isProcessing" class="m-2" variant="info" show>
                            <LoadingSpan message="Processing operation" />
                        </b-alert>
                        <div v-else-if="historyItems.length === 0">
                            <HistoryEmpty v-if="queryDefault" :writable="canEditHistory" class="m-2" />

                            <b-alert v-else-if="formattedSearchError" class="m-2" variant="danger" show>
                                Error in filter:
                                <a href="javascript:void(0)" @click="showAdvanced = true">
                                    {{ formattedSearchError.filter }}'{{ formattedSearchError.value }}'
                                </a>
                            </b-alert>
                            <b-alert v-else class="m-2" variant="info" show>
                                No data found for selected filter.
                            </b-alert>
                        </div>
                        <ListingLayout
                            v-else
                            :offset="listOffset"
                            :items="historyItems"
                            :query-key="queryKey"
                            @scroll="onScroll">
                            <template v-slot:item="{ item, currentOffset }">
                                <ContentItem
                                    v-if="!invisibleHistoryItems[item.hid]"
                                    :id="item.hid"
                                    is-history-item
                                    :item="item"
                                    :name="item.name"
                                    :writable="canEditHistory"
                                    :expand-dataset="isExpanded(item)"
                                    :is-dataset="isDataset(item)"
                                    :highlight="getHighlight(item)"
                                    :selected="isSelected(item)"
                                    :selectable="showSelection"
                                    :filterable="filterable"
                                    @tag-click="updateFilterValue('tag', $event)"
                                    @tag-change="onTagChange"
                                    @toggleHighlights="updateFilterValue('related', item.hid)"
                                    @update:expand-dataset="setExpanded(item, $event)"
                                    @update:selected="setSelected(item, $event)"
                                    @view-collection="$emit('view-collection', item, currentOffset)"
                                    @delete="onDelete"
                                    @undelete="onUndelete(item)"
                                    @unhide="onUnhide(item)" />
                            </template>
                        </ListingLayout>
                    </div>
                </section>
            </section>
        </SelectedItems>
    </ExpandedItems>
</template>
