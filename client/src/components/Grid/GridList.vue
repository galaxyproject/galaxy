<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown, faCaretUp, faShieldAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useDebounceFn, useEventBus } from "@vueuse/core";
import { BAlert, BButton, BCard, BFormCheckbox, BOverlay, BPagination } from "bootstrap-vue";
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import {
    type BatchOperation,
    type FieldEntry,
    type FieldHandler,
    type GridConfig,
    type Operation,
    type RowData,
} from "./configs/types";

import HelpText from "../Help/HelpText.vue";
import SwitchToHistoryLink from "../History/SwitchToHistoryLink.vue";
import GridBoolean from "./GridElements/GridBoolean.vue";
import GridDatasets from "./GridElements/GridDatasets.vue";
import GridExpand from "./GridElements/GridExpand.vue";
import GridLink from "./GridElements/GridLink.vue";
import GridOperations from "./GridElements/GridOperations.vue";
import GridText from "./GridElements/GridText.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";
import Heading from "@/components/Common/Heading.vue";
import SharingIndicators from "@/components/Indices/SharingIndicators.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import UtcDate from "@/components/UtcDate.vue";

const eventBus = useEventBus<string>("grid-router-push");
const router = useRouter();

library.add(faCaretDown, faCaretUp, faShieldAlt);

interface Props {
    // provide a grid configuration
    gridConfig: GridConfig;
    // incoming initial message
    gridMessage?: string;
    // no data message
    noDataMessage?: string;
    // debounce delay
    delay?: number;
    // embedded
    embedded?: boolean;
    // rows per page to be shown
    limit?: number;
    // username for initial search
    usernameSearch?: string;
    // any extra props to be passed to `getData`
    extraProps?: Record<string, unknown>;
}

const props = withDefaults(defineProps<Props>(), {
    delay: 5000,
    embedded: false,
    limit: 25,
    gridMessage: "",
    noDataMessage: "No data available.",
    usernameSearch: "",
    extraProps: undefined,
});

// contains the current grid data provided by the corresponding api endpoint
const gridData = ref();

// message references
const errorMessage = ref("");
const operationMessage = ref("");
const operationStatus = ref("");

// selection references
const selected = ref(new Set<RowData>());
const selectedAll = computed(() => gridData.value.length === selected.value.size);
const selectedIndeterminate = computed(() => ![0, gridData.value.length].includes(selected.value.size));

// expand references
const expanded = ref(new Set<RowData>());

// page references
const currentPage = ref(1);
const totalRows = ref(0);

// loading indicators
const initDataLoading = ref(true);
const resultsLoading = ref(false);

// check if `initDataLoading` has completed and data rows are available
const isAvailable = computed(() => !initDataLoading.value && totalRows.value > 0);

// sort references
const sortBy = ref(props.gridConfig ? props.gridConfig.sortBy : "");
const sortDesc = ref(props.gridConfig ? props.gridConfig.sortDesc : false);

// filtering refs and handlers
const filterText = ref("");
const showAdvanced = ref(false);
const filterClass = props.gridConfig.filtering;
const rawFilters = computed(() =>
    Object.fromEntries(filterClass?.getFiltersForText(filterText.value, true, false) || [])
);
const validFilters = computed(() => filterClass?.getValidFilters(rawFilters.value, true).validFilters);
const invalidFilters = computed(() => filterClass?.getValidFilters(rawFilters.value, true).invalidFilters);
const isSurroundedByQuotes = computed(() => /^["'].*["']$/.test(filterText.value));
const hasInvalidFilters = computed(
    () => !isSurroundedByQuotes.value && Object.keys(invalidFilters.value || {}).length > 0
);

// hide message helper
const hideMessage = useDebounceFn(() => {
    operationMessage.value = "";
}, props.delay);

/**
 * Manually set filter value, used for tags and `SharingIndicators`
 */
function applyFilter(filter: string, value: string | boolean, quoted = false) {
    const filtering = props.gridConfig?.filtering;
    const quotedValue = quoted ? `'${value}'` : value;
    if (filtering) {
        filterText.value = filtering.setFilterValue(filterText.value, filter, quotedValue.toString()) || "";
    }
}

/**
 * Display initial message parsed through route query
 */
function displayInitialMessage() {
    if (props.gridMessage) {
        operationMessage.value = props.gridMessage;
        operationStatus.value = "success";
    }
}

/**
 * Returns the appropriate text for a field entry
 */
function fieldText(fieldEntry: FieldEntry, rowData: RowData): string {
    if (fieldEntry.converter) {
        return fieldEntry.converter(rowData);
    } else {
        return rowData[fieldEntry.key] as string;
    }
}

/**
 * Returns the appropriate column header title for a field entry
 */
function fieldTitle(fieldEntry: FieldEntry): string | null {
    if (fieldEntry.title) {
        return fieldEntry.title;
    } else if (fieldEntry.title === undefined || fieldEntry.title === "") {
        return fieldEntry.key.charAt(0).toUpperCase() + fieldEntry.key.slice(1).replace(/_/g, " ").toLowerCase();
    } else {
        return null;
    }
}

/**
 * Request grid data
 */
async function getGridData() {
    resultsLoading.value = true;
    selected.value = new Set();
    if (props.gridConfig) {
        if (hasInvalidFilters.value) {
            // there are invalid filters, so we don't want to search
            initDataLoading.value = false;
            resultsLoading.value = false;
            return;
        }
        try {
            const offset = props.limit * (currentPage.value - 1);
            const [responseData, responseTotal] = await props.gridConfig.getData(
                offset,
                props.limit,
                validatedFilterText(),
                sortBy.value,
                sortDesc.value,
                props.extraProps
            );
            gridData.value = responseData;
            totalRows.value = responseTotal;
            errorMessage.value = "";
        } catch (e) {
            errorMessage.value = `Failed to obtain grid data: ${e}`;
        } finally {
            initDataLoading.value = false;
            resultsLoading.value = false;
        }
    }
}

/**
 * Execute grid operation and display message if available
 */
async function onBatchOperation(operation: BatchOperation, rowDataArray: Array<RowData>) {
    const response = await operation.handler(rowDataArray);
    if (response) {
        await getGridData();
        operationMessage.value = response.message;
        operationStatus.value = response.status || "success";
    }
}

async function onOperation(operation: Operation, rowData: RowData) {
    const response = await operation.handler(rowData);
    if (response) {
        await getGridData();
        operationMessage.value = response.message;
        operationStatus.value = response.status || "success";
    }
}

/**
 * Handle router push request emitted by grid module
 */
function onRouterPush(route: string, options = {}) {
    // reset expanded rows before navigating
    expanded.value = new Set();
    // @ts-ignore
    nextTick(() => {
        // @ts-ignore
        router.push(route, options);
    });
}

/**
 * User changes sorting
 */
function onSort(sortKey: string) {
    if (sortBy.value !== sortKey) {
        sortBy.value = sortKey;
        sortDesc.value = false;
    } else {
        sortDesc.value = !sortDesc.value;
    }
}

/**
 * Process tag inputs
 */
function onTagInput(data: RowData, tags: Array<string>, tagsHandler?: FieldHandler) {
    if (tagsHandler) {
        tagsHandler({ ...data, tags: tags });
        data.tags = tags;
    }
}
function onFilter(filter?: string) {
    if (filter) {
        applyFilter(filter, true);
    }
}

// Select multiple rows
function onSelect(rowData: RowData) {
    if (selected.value.has(rowData)) {
        selected.value.delete(rowData);
    } else {
        selected.value.add(rowData);
    }
    selected.value = new Set(selected.value);
}

function onSelectAll(current: boolean): void {
    if (current) {
        selected.value = new Set(gridData.value);
    } else {
        selected.value = new Set();
    }
}

/**
 * Show details for a row
 */
function showDetails(rowData: RowData, show: boolean) {
    if (show) {
        expanded.value.add(rowData);
    } else {
        expanded.value.delete(rowData);
    }
    expanded.value = new Set(expanded.value);
}

/**
 * A valid filter/query for the backend
 */
function validatedFilterText() {
    if (isSurroundedByQuotes.value) {
        // the filterText is surrounded by quotes, remove them
        return filterText.value.slice(1, -1);
    } else if (Object.keys(rawFilters.value).length === 0) {
        // there are no filters derived from the `filterText`
        return filterText.value;
    }
    // there are valid filters derived from the `filterText`
    return filterClass?.getFilterText(validFilters.value || {}, false) || "";
}

/**
 * Initialize grid data
 */
onMounted(() => {
    if (props.usernameSearch) {
        filterText.value = filterClass?.setFilterValue(filterText.value, "user", `'${props.usernameSearch}'`) || "";
    }
    getGridData();
    eventBus.on(onRouterPush);
    displayInitialMessage();
});

onUnmounted(() => {
    eventBus.off(onRouterPush);
});

/**
 * Load current page
 */
watch([currentPage, filterText, sortDesc, sortBy], () => getGridData());

/**
 * Operation message timeout handler
 */
watch(operationMessage, () => {
    hideMessage();
});
</script>

<template>
    <div :id="gridConfig.id" class="d-flex flex-column overflow-auto">
        <BAlert v-if="!!errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
        <BAlert v-if="!!operationMessage" :variant="operationStatus" fade show>{{ operationMessage }}</BAlert>
        <div v-if="!embedded || filterClass" class="grid-header d-flex justify-content-between pb-2 flex-column">
            <div v-if="!embedded" class="d-flex">
                <Heading h1 separator inline size="xl" class="flex-grow-1 m-0" data-description="grid title">
                    <span v-localize>{{ gridConfig.title }}</span>
                </Heading>
                <div class="d-flex justify-content-between">
                    <BButton
                        v-for="(action, actionIndex) in gridConfig.actions"
                        :key="actionIndex"
                        class="m-1"
                        size="sm"
                        variant="outline-primary"
                        :data-description="`grid action ${action.title.toLowerCase()}`"
                        @click="action.handler()">
                        <Icon :icon="action.icon" class="mr-1" />
                        <span v-localize>{{ action.title }}</span>
                    </BButton>
                </div>
            </div>
            <FilterMenu
                v-if="filterClass"
                :class="{ 'py-2': !embedded }"
                :name="gridConfig.plural"
                :placeholder="`search ${gridConfig.plural.toLowerCase()}`"
                :filter-class="filterClass"
                :filter-text.sync="filterText"
                :loading="initDataLoading || resultsLoading"
                :show-advanced.sync="showAdvanced"
                view="compact" />
        </div>
        <LoadingSpan v-if="initDataLoading" />
        <span v-else-if="!isAvailable || hasInvalidFilters">
            <BAlert v-if="!hasInvalidFilters" variant="info" show>
                <span v-if="filterText">
                    <span v-localize>Nothing found with:</span>
                    <b>{{ filterText }}</b>
                </span>
                <span v-else v-localize>{{ noDataMessage }}</span>
            </BAlert>
            <BAlert v-else-if="invalidFilters" variant="danger" show>
                <Heading h4 inline size="sm" class="flex-grow-1 mb-2">Invalid filters in query:</Heading>
                <ul>
                    <li v-for="[invalidKey, value] in Object.entries(invalidFilters)" :key="invalidKey">
                        <b>{{ invalidKey }}</b
                        >: {{ value }}
                    </li>
                </ul>
                <a href="javascript:void(0)" class="ui-link" @click="filterText = validatedFilterText()">
                    Remove invalid filters from query
                </a>
                or
                <a
                    v-b-tooltip.noninteractive.hover
                    title="Note that this might produce inaccurate results"
                    href="javascript:void(0)"
                    class="ui-link"
                    @click="filterText = `'${filterText}'`">
                    Match the exact query provided
                </a>
            </BAlert>
        </span>
        <BOverlay v-else :show="resultsLoading" rounded="sm">
            <table class="grid-table">
                <thead>
                    <th v-if="!!gridConfig.batch">
                        <BFormCheckbox
                            class="m-2"
                            :checked="selectedAll"
                            :indeterminate="selectedIndeterminate"
                            @change="onSelectAll" />
                    </th>
                    <th
                        v-for="(fieldEntry, fieldIndex) in gridConfig.fields"
                        :key="fieldIndex"
                        class="text-nowrap px-2"
                        :data-description="`grid header ${fieldIndex}`">
                        <span v-if="gridConfig.sortKeys.includes(fieldEntry.key)">
                            <BButton
                                variant="link"
                                class="text-nowrap font-weight-bold p-0"
                                :data-description="`grid sort key ${fieldEntry.key}`"
                                @click="onSort(fieldEntry.key)">
                                <span>{{ fieldTitle(fieldEntry) }}</span>
                                <span v-if="sortBy === fieldEntry.key">
                                    <FontAwesomeIcon
                                        v-if="sortDesc"
                                        icon="caret-down"
                                        data-description="grid sort desc" />
                                    <FontAwesomeIcon v-else icon="caret-up" data-description="grid sort asc" />
                                </span>
                            </BButton>
                        </span>
                        <span v-else-if="fieldTitle(fieldEntry)">{{ fieldTitle(fieldEntry) }}</span>
                    </th>
                </thead>
                <tbody v-for="(rowData, rowIndex) in gridData" :key="rowIndex" data-description="grid item">
                    <tr :class="{ 'grid-dark-row': rowIndex % 2 }">
                        <td v-if="!!gridConfig.batch">
                            <BFormCheckbox
                                :checked="selected.has(rowData)"
                                class="m-2 cursor-pointer"
                                data-description="grid selected"
                                @change="onSelect(rowData)" />
                        </td>
                        <td
                            v-for="(fieldEntry, fieldIndex) in gridConfig.fields"
                            :key="fieldIndex"
                            class="px-2 py-3"
                            :style="{ width: `${fieldEntry.width}%` }">
                            <div
                                v-if="!fieldEntry.condition || fieldEntry.condition(rowData)"
                                :data-description="`grid cell ${rowIndex}-${fieldIndex}`">
                                <GridOperations
                                    v-if="fieldEntry.type == 'operations' && fieldEntry.operations"
                                    :operations="fieldEntry.operations"
                                    :row-data="rowData"
                                    :title="rowData[fieldEntry.key]"
                                    @execute="onOperation($event, rowData)" />
                                <GridExpand
                                    v-else-if="fieldEntry.type == 'expand'"
                                    :details-showing="expanded.has(rowData)"
                                    @show-details="(s) => showDetails(rowData, s)" />
                                <GridBoolean
                                    v-else-if="fieldEntry.type == 'boolean'"
                                    :value="rowData[fieldEntry.key]" />
                                <GridDatasets
                                    v-else-if="fieldEntry.type == 'datasets'"
                                    :history-id="rowData[fieldEntry.key]" />
                                <GridText
                                    v-else-if="fieldEntry.type == 'text'"
                                    :text="fieldText(fieldEntry, rowData)" />
                                <GridLink
                                    v-else-if="fieldEntry.type == 'link'"
                                    :text="fieldText(fieldEntry, rowData)"
                                    @click="fieldEntry.handler && fieldEntry.handler(rowData)" />
                                <BButton
                                    v-else-if="fieldEntry.type == 'button'"
                                    class="d-flex flex-inline flex-gapx-1 align-items-center"
                                    variant="primary"
                                    @click="fieldEntry.handler && fieldEntry.handler(rowData)">
                                    <FontAwesomeIcon v-if="fieldEntry.icon" :icon="fieldEntry.icon" />
                                    <span v-if="fieldText(fieldEntry, rowData)" v-localize>{{
                                        fieldText(fieldEntry, rowData)
                                    }}</span>
                                </BButton>
                                <SwitchToHistoryLink
                                    v-else-if="fieldEntry.type == 'history'"
                                    :history-id="rowData[fieldEntry.key]" />
                                <HelpText
                                    v-else-if="fieldEntry.type == 'helptext' && fieldEntry.converter"
                                    :uri="fieldEntry.converter(rowData)"
                                    :text="rowData[fieldEntry.key]" />
                                <SharingIndicators
                                    v-else-if="fieldEntry.type == 'sharing'"
                                    :object="rowData"
                                    @filter="onFilter($event)" />
                                <UtcDate
                                    v-else-if="fieldEntry.type == 'date'"
                                    :date="rowData[fieldEntry.key]"
                                    mode="elapsed" />
                                <StatelessTags
                                    v-else-if="fieldEntry.type == 'tags'"
                                    clickable
                                    :value="rowData[fieldEntry.key]"
                                    :disabled="fieldEntry.disabled"
                                    @input="onTagInput(rowData, $event, fieldEntry.handler)"
                                    @tag-click="applyFilter('tag', $event, true)" />
                                <span v-else v-localize> Not available. </span>
                            </div>
                            <FontAwesomeIcon v-else icon="fa-shield-alt" />
                        </td>
                    </tr>
                    <tr v-if="expanded.has(rowData)" data-description="grid expanded row">
                        <td :colspan="gridConfig.fields.length + 2">
                            <BCard class="p-2">
                                <slot name="expanded" :row-data="rowData" />
                            </BCard>
                        </td>
                    </tr>
                </tbody>
            </table>
        </BOverlay>
        <div class="flex-grow-1 h-100" />
        <div class="grid-footer">
            <div v-if="isAvailable" class="d-flex justify-content-between pt-3">
                <div class="d-flex">
                    <div v-for="(batchOperation, batchIndex) in gridConfig.batch" :key="batchIndex">
                        <BButton
                            v-if="
                                selected.size > 0 &&
                                (!batchOperation.condition || batchOperation.condition(Array.from(selected)))
                            "
                            class="mr-2"
                            size="sm"
                            variant="primary"
                            :data-description="`grid batch ${batchOperation.title.toLowerCase()}`"
                            @click="onBatchOperation(batchOperation, Array.from(selected))">
                            <Icon :icon="batchOperation.icon" class="mr-1" />
                            <span v-localize>{{ batchOperation.title }} ({{ selected.size }})</span>
                        </BButton>
                    </div>
                </div>
                <BPagination
                    v-model="currentPage"
                    :total-rows="totalRows"
                    :per-page="limit"
                    class="m-0"
                    size="sm"
                    data-description="grid pager"
                    next-class="gx-grid-pager-next"
                    prev-class="gx-grid-pager-prev"
                    first-class="gx-grid-pager-first"
                    last-class="gx-grid-pager-last"
                    page-class="gx-grid-pager-page" />
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.grid-footer {
    @extend .grid-sticky;
    bottom: 0;
}
.grid-header {
    @extend .grid-sticky;
    top: 0;
}
.grid-sticky {
    left: 0;
    z-index: 2;
    background: $white;
    opacity: 0.95;
    position: sticky;
}
.grid-dark-row {
    background: $gray-200;
}
</style>
