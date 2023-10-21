<script setup lang="ts">
import { BAlert, BButton, BLink, BPagination } from "bootstrap-vue";
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { timeout } from "@/utils/timeout";

import { registry } from "./configs/registry";
import { FieldKeyHandler, Operation, RowData } from "./configs/types";

import GridOperations from "./GridElements/GridOperations.vue";
import GridSharing from "./GridElements/GridSharing.vue";
import GridText from "./GridElements/GridText.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
//@ts-ignore
import UtcDate from "@/components/UtcDate.vue";

const router = useRouter();

interface Props {
    // specifies the grid config identifier as specified in the registry
    id: string;
    // rows per page to be shown
    perPage?: number;
}

const props = withDefaults(defineProps<Props>(), {
    perPage: 5,
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

// current grid configuration
const gridConfig = computed(() => {
    return registry[props.id];
});

// check if loading has completed and data rows are available
const isAvailable = computed(() => !loading.value && totalRows.value > 0);

// sort references
const sortBy = ref(gridConfig.value ? gridConfig.value.sortBy : "");
const sortDesc = ref(gridConfig.value ? gridConfig.value.sortDesc : false);

// filtering refs and handlers
const filterText = ref("");
const searchTerm = ref("");
const showAdvanced = ref(false);

/**
 * Manually set filter value, used for tags
 */
function applyFilter(filter: string, value: string, quoted = false) {
    const setFilterValue = gridConfig.value?.filtering.setFilterValue;
    const quotedValue = quoted ? `'${value}'` : value;
    if (setFilterValue) {
        filterText.value = setFilterValue(filterText.value, filter, quotedValue) || "";
    }
}

/**
 * Request grid data
 */
async function getGridData() {
    if (gridConfig.value) {
        try {
            const response = await gridConfig.value.getData(
                currentPage.value,
                props.perPage,
                sortBy.value,
                sortDesc.value,
                searchTerm.value
            );
            if (response.headers.total_matches) {
                totalRows.value = parseInt(response.headers.total_matches);
            }
            gridData.value = response.data;
            errorMessage.value = "";
            loading.value = false;
        } catch (e) {
            errorMessage.value = "Failed to obtain grid data.";
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
async function onTagInput(data: RowData, tags: Array<string>, tagsHandler: FieldKeyHandler) {
    await tagsHandler({ ...data, tags: tags });
    data.tags = tags;
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
                <h1 class="m-0">
                    {{ gridConfig.title }}
                </h1>
                <FilterMenu
                    class="py-2"
                    :name="gridConfig.plural"
                    placeholder="search visualizations"
                    :filter-class="gridConfig.filtering"
                    :filter-text.sync="filterText"
                    :loading="loading"
                    :show-advanced.sync="showAdvanced"
                    @on-backend-filter="onSearch" />
                <hr v-if="showAdvanced" />
            </div>
            <div v-if="!showAdvanced" class="py-3">
                <BButton
                    v-for="(action, actionIndex) in gridConfig.actions"
                    :key="actionIndex"
                    class="m-1"
                    size="sm"
                    variant="primary"
                    @click="action.handler(router)">
                    <icon :icon="action.icon" class="mr-1" />
                    <span v-localize>Create</span>
                </BButton>
            </div>
        </div>
        <LoadingSpan v-if="loading" />
        <BAlert v-else-if="!isAvailable" v-localize variant="info" show>No entries found.</BAlert>
        <table v-else class="grid-table">
            <thead>
                <th v-for="(fieldEntry, fieldIndex) in gridConfig.fields" :key="fieldIndex" class="text-nowrap px-2">
                    <span v-if="gridConfig.sortKeys.includes(fieldEntry.key)">
                        <BLink @click="onSort(fieldEntry.key)">
                            <span>{{ fieldEntry.title || fieldEntry.key }}</span>
                            <span v-if="sortBy === fieldEntry.key">
                                <icon v-if="sortDesc" icon="caret-up" />
                                <icon v-else icon="caret-down" />
                            </span>
                        </BLink>
                    </span>
                    <span v-else>{{ fieldEntry.title || fieldEntry.key }}</span>
                </th>
            </thead>
            <tr v-for="(rowData, rowIndex) in gridData" :key="rowIndex" :class="{ 'grid-dark-row': rowIndex % 2 }">
                <td
                    v-for="(fieldEntry, fieldIndex) in gridConfig.fields"
                    :key="fieldIndex"
                    class="px-2 py-3"
                    :style="{ width: fieldEntry.width }">
                    <GridOperations
                        v-if="fieldEntry.type == 'operations'"
                        :title="rowData.title"
                        :operations="fieldEntry.operations"
                        @execute="onOperation($event, rowData)" />
                    <GridText v-else-if="fieldEntry.type == 'text'" :text="rowData[fieldEntry.key]" />
                    <GridSharing
                        v-else-if="fieldEntry.type == 'sharing'"
                        :published="rowData.sharing_status.published"
                        :importable="rowData.sharing_status.importable"
                        :users_shared_with_length="rowData.sharing_status.users_shared_with.length" />
                    <UtcDate v-else-if="fieldEntry.type == 'date'" :date="rowData[fieldEntry.key]" mode="elapsed" />
                    <StatelessTags
                        v-else-if="fieldEntry.type == 'tags'"
                        clickable
                        :value="rowData[fieldEntry.key]"
                        :disabled="rowData.published"
                        @input="(tags) => onTagInput(rowData, tags, fieldEntry.handler)"
                        @tag-click="(t) => applyFilter('tag', t, true)" />
                </td>
            </tr>
        </table>
        <div class="flex-grow-1 h-100" />
        <div v-if="isAvailable" class="grid-footer d-flex justify-content-center pt-3">
            <BPagination
                v-model="currentPage"
                :total-rows="totalRows"
                :per-page="perPage"
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
