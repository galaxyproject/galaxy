<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown, faCaretUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BLink, BPagination } from "bootstrap-vue";
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { timeout } from "@/utils/timeout";

import { Config, FieldHandler, Operation, RowData } from "./configs/types";

import GridLink from "./GridElements/GridLink.vue";
import GridOperations from "./GridElements/GridOperations.vue";
import GridText from "./GridElements/GridText.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";
import SharingIndicators from "@/components/Indices/SharingIndicators.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import UtcDate from "@/components/UtcDate.vue";

library.add(faCaretDown, faCaretUp);
const router = useRouter();

interface Props {
    // provide a grid configuration
    config: Config;
    // rows per page to be shown
    limit?: number;
}

const props = withDefaults(defineProps<Props>(), {
    limit: 25,
});

// contains the current grid data provided by the corresponding api endpoint
const gridData = ref();

// message references
const errorMessage = ref("");
const operationMessage = ref("");
const operationStatus = ref("");

// page references
const currentPage = ref(1);
const totalRows = ref(0);

// loading indicator
const loading = ref(true);

// check if loading has completed and data rows are available
const isAvailable = computed(() => !loading.value && totalRows.value > 0);

// sort references
const sortBy = ref(props.config ? props.config.sortBy : "");
const sortDesc = ref(props.config ? props.config.sortDesc : false);

// filtering refs and handlers
const filterText = ref("");
const searchTerm = ref("");
const showAdvanced = ref(false);

/**
 * Manually set filter value, used for tags and `SharingIndicators`
 */
function applyFilter(filter: string, value: string | boolean, quoted = false) {
    const filtering = props.config?.filtering;
    const quotedValue = quoted ? `'${value}'` : value;
    if (filtering) {
        filterText.value = filtering.setFilterValue(filterText.value, filter, quotedValue.toString()) || "";
    }
}

/**
 * Request grid data
 */
async function getGridData() {
    if (props.config) {
        try {
            const offset = props.limit * (currentPage.value - 1);
            const [responseData, responseTotal] = await props.config.getData(
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
async function onOperation(operation: Operation, rowData: RowData) {
    const response = await operation.handler(rowData, router);
    if (response) {
        await getGridData();
        operationMessage.value = response.message;
        operationStatus.value = response.status || "success";
    }
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
/**
 * Initialize grid data
 */
onMounted(() => {
    getGridData();
});

/**
 * Load current page
 */
watch([currentPage, searchTerm, sortDesc, sortBy], () => getGridData());

/**
 * Operation message timeout handler
 */
watch(operationMessage, () => {
    timeout(() => {
        operationMessage.value = "";
    });
});
</script>

<template>
    <div class="d-flex flex-column overflow-auto">
        <BAlert v-if="!!errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
        <BAlert v-if="!!operationMessage" :variant="operationStatus" fade show>{{ operationMessage }}</BAlert>
        <div class="grid-header d-flex justify-content-between pb-2">
            <div>
                <h1 class="m-0" data-description="grid title">
                    {{ config.title }}
                </h1>
                <FilterMenu
                    class="py-2"
                    :name="config.plural"
                    :placeholder="`search ${config.plural.toLowerCase()}`"
                    :filter-class="config.filtering"
                    :filter-text.sync="filterText"
                    :loading="loading"
                    :show-advanced.sync="showAdvanced"
                    @on-backend-filter="onSearch" />
                <hr v-if="showAdvanced" />
            </div>
            <div v-if="!showAdvanced" class="py-3">
                <BButton
                    v-for="(action, actionIndex) in config.actions"
                    :key="actionIndex"
                    class="m-1"
                    size="sm"
                    variant="primary"
                    :data-description="`grid action ${action.title.toLowerCase()}`"
                    @click="action.handler(router)">
                    <Icon :icon="action.icon" class="mr-1" />
                    <span v-localize>{{ action.title }}</span>
                </BButton>
            </div>
        </div>
        <LoadingSpan v-if="loading" />
        <BAlert v-else-if="!isAvailable" variant="info" show>
            <span v-if="searchTerm" v-localize>
                No entries found for: <b>{{ searchTerm }}</b
                >.
            </span>
            <span v-else v-localize> No entries found. </span>
        </BAlert>
        <table v-else class="grid-table">
            <thead>
                <th
                    v-for="(fieldEntry, fieldIndex) in config.fields"
                    :key="fieldIndex"
                    class="text-nowrap px-2"
                    :data-description="`grid header ${fieldIndex}`">
                    <span v-if="config.sortKeys.includes(fieldEntry.key)">
                        <BLink @click="onSort(fieldEntry.key)">
                            <span>{{ fieldEntry.title || fieldEntry.key }}</span>
                            <span v-if="sortBy === fieldEntry.key">
                                <FontAwesomeIcon v-if="sortDesc" icon="caret-up" data-description="grid sort asc" />
                                <FontAwesomeIcon v-else icon="caret-down" data-description="grid sort desc" />
                            </span>
                        </BLink>
                    </span>
                    <span v-else>{{ fieldEntry.title || fieldEntry.key }}</span>
                </th>
            </thead>
            <tr v-for="(rowData, rowIndex) in gridData" :key="rowIndex" :class="{ 'grid-dark-row': rowIndex % 2 }">
                <td
                    v-for="(fieldEntry, fieldIndex) in config.fields"
                    :key="fieldIndex"
                    class="px-2 py-3"
                    :style="{ width: `${fieldEntry.width}%` }"
                    :data-description="`grid cell ${rowIndex}-${fieldIndex}`">
                    <GridOperations
                        v-if="fieldEntry.type == 'operations'"
                        :operations="fieldEntry.operations"
                        :row-data="rowData"
                        @execute="onOperation($event, rowData)" />
                    <GridText v-else-if="fieldEntry.type == 'text'" :text="rowData[fieldEntry.key]" />
                    <GridLink
                        v-else-if="fieldEntry.type == 'link'"
                        :text="rowData[fieldEntry.key]"
                        @click="fieldEntry.handler && fieldEntry.handler(rowData, router)" />
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
                    <span v-else v-localize> Data not available. </span>
                </td>
            </tr>
        </table>
        <div class="flex-grow-1 h-100" />
        <div v-if="isAvailable" class="grid-footer d-flex justify-content-center pt-3">
            <BPagination
                v-model="currentPage"
                :total-rows="totalRows"
                :per-page="limit"
                class="m-0"
                size="sm"
                aria-controls="grid-table" />
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
    z-index: 1;
    background: $white;
    opacity: 0.95;
    position: sticky;
}
.grid-dark-row {
    background: $gray-200;
}
</style>
