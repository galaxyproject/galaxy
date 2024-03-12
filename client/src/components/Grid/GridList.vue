<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown, faCaretUp, faShieldAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useDebounceFn, useEventBus } from "@vueuse/core";
import { BAlert, BButton, BFormCheckbox, BPagination } from "bootstrap-vue";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { BatchOperation, FieldHandler, GridConfig, Operation, RowData } from "./configs/types";

import GridBoolean from "./GridElements/GridBoolean.vue";
import GridDatasets from "./GridElements/GridDatasets.vue";
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
    // debounce delay
    delay?: number;
    // embedded
    embedded?: boolean;
    // rows per page to be shown
    limit?: number;
    // username for initial search
    usernameSearch?: string;
}

const props = withDefaults(defineProps<Props>(), {
    delay: 5000,
    embedded: false,
    limit: 25,
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

// page references
const currentPage = ref(1);
const totalRows = ref(0);

// loading indicator
const loading = ref(true);

// check if loading has completed and data rows are available
const isAvailable = computed(() => !loading.value && totalRows.value > 0);

// sort references
const sortBy = ref(props.gridConfig ? props.gridConfig.sortBy : "");
const sortDesc = ref(props.gridConfig ? props.gridConfig.sortDesc : false);

// filtering refs and handlers
const filterText = ref("");
const searchTerm = ref("");
const showAdvanced = ref(false);

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
 * Request grid data
 */
async function getGridData() {
    selected.value = new Set();
    if (props.gridConfig) {
        try {
            const offset = props.limit * (currentPage.value - 1);
            const [responseData, responseTotal] = await props.gridConfig.getData(
                offset,
                props.limit,
                searchTerm.value,
                sortBy.value,
                sortDesc.value
            );
            gridData.value = responseData;
            totalRows.value = responseTotal;
            errorMessage.value = "";
            loading.value = false;
        } catch (e) {
            errorMessage.value = `Failed to obtain grid data: ${e}`;
            loading.value = false;
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
function onRouterPush(route: string) {
    router.push(route);
}

/**
 * Apply backend formatted filter and execute grid search
 */
function onSearch(query: string) {
    searchTerm.value = query;
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
 * Initialize grid data
 */
onMounted(() => {
    if (props.usernameSearch) {
        const search_query = `user:${props.usernameSearch}`.trim();
        filterText.value = search_query;
        onSearch(search_query);
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
watch([currentPage, searchTerm, sortDesc, sortBy], () => getGridData());

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
        <div class="grid-header d-flex justify-content-between pb-2 flex-column">
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
                :class="{ 'py-2': !embedded }"
                :name="gridConfig.plural"
                :placeholder="`search ${gridConfig.plural.toLowerCase()}`"
                :filter-class="gridConfig.filtering"
                :filter-text.sync="filterText"
                :loading="loading"
                :show-advanced.sync="showAdvanced"
                @on-backend-filter="onSearch" />
            <hr v-if="showAdvanced" />
        </div>
        <LoadingSpan v-if="loading" />
        <BAlert v-else-if="!isAvailable" variant="info" show>
            <span v-if="searchTerm">
                <span v-localize>Nothing found with:</span>
                <b>{{ searchTerm }}</b>
            </span>
            <span v-else v-localize> No entries found. </span>
        </BAlert>
        <table v-else class="grid-table">
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
                            class="text-nowrap font-weight-bold"
                            :data-description="`grid sort key ${fieldEntry.key}`"
                            @click="onSort(fieldEntry.key)">
                            <span>{{ fieldEntry.title || fieldEntry.key }}</span>
                            <span v-if="sortBy === fieldEntry.key">
                                <FontAwesomeIcon v-if="sortDesc" icon="caret-down" data-description="grid sort desc" />
                                <FontAwesomeIcon v-else icon="caret-up" data-description="grid sort asc" />
                            </span>
                        </BButton>
                    </span>
                    <span v-else>{{ fieldEntry.title || fieldEntry.key }}</span>
                </th>
            </thead>
            <tr v-for="(rowData, rowIndex) in gridData" :key="rowIndex" :class="{ 'grid-dark-row': rowIndex % 2 }">
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
                        <GridBoolean v-else-if="fieldEntry.type == 'boolean'" :value="rowData[fieldEntry.key]" />
                        <GridDatasets v-else-if="fieldEntry.type == 'datasets'" :history-id="rowData[fieldEntry.key]" />
                        <GridText v-else-if="fieldEntry.type == 'text'" :text="rowData[fieldEntry.key]" />
                        <GridLink
                            v-else-if="fieldEntry.type == 'link'"
                            :text="rowData[fieldEntry.key]"
                            @click="fieldEntry.handler && fieldEntry.handler(rowData)" />
                        <SharingIndicators
                            v-else-if="fieldEntry.type == 'sharing'"
                            :object="rowData"
                            @filter="onFilter($event)" />
                        <UtcDate v-else-if="fieldEntry.type == 'date'" :date="rowData[fieldEntry.key]" mode="elapsed" />
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
        </table>
        <div class="flex-grow-1 h-100" />
        <div class="grid-footer">
            <div v-if="isAvailable && gridConfig.batch" class="d-flex justify-content-between pt-3">
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
                <BPagination v-model="currentPage" :total-rows="totalRows" :per-page="limit" class="m-0" size="sm" />
            </div>
            <div v-else-if="isAvailable" class="d-flex justify-content-center pt-3">
                <BPagination v-model="currentPage" :total-rows="totalRows" :per-page="limit" class="m-0" size="sm" />
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
    z-index: 2;
    background: $white;
    opacity: 0.95;
    position: sticky;
}
.grid-dark-row {
    background: $gray-200;
}
</style>
