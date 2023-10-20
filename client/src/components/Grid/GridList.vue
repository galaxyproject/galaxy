<script setup lang="ts">
import axios from "axios";
import { BAlert } from "bootstrap-vue";
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { withPrefix } from "@/utils/redirect";
import { timeout } from "@/utils/timeout";

import { registry } from "./configs/registry";
import { FieldKeyHandler, Operation, RowData } from "./configs/types";

import GridOperations from "./GridElements/GridOperations.vue";
import GridSharing from "./GridElements/GridSharing.vue";
import GridText from "./GridElements/GridText.vue";
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

/**
 * Request grid data
 */
async function getGridData() {
    if (gridConfig.value) {
        try {
            const response = await axios.get(withPrefix(gridConfig.value.getUrl(currentPage.value, props.perPage, "")));
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
async function executeOperation(operation: Operation, rowData: RowData) {
    const response = await operation.handler(rowData, router);
    if (response) {
        await getGridData();
        operationMessage.value = response.message;
        operationStatus.value = response.status || "success";
    }
}

/**
 * Process tag inputs
 */
async function onTagInput(data: RowData, tags: Array<string>, tagsHandler: FieldKeyHandler) {
    await tagsHandler({ ...data, tags: tags });
    data.tags = tags;
}

function onTagClick() {}

/**
 * Initialize grid data
 */
onMounted(() => {
    getGridData();
});

/**
 * Load current page
 */
watch(currentPage, () => getGridData());

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
    <div class="grid-list">
        <BAlert v-if="!!errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
        <BAlert v-if="!!operationMessage" :variant="operationStatus" fade show>{{ operationMessage }}</BAlert>
        <div class="grid-header">
            <h1>
                {{ gridConfig.title }}
            </h1>
        </div>
        <LoadingSpan v-if="loading" />
        <BAlert v-else-if="!isAvailable" v-localize variant="info" show>No entries found.</BAlert>
        <table v-else class="grid-table">
            <thead>
                <th v-for="(fieldEntry, fieldIndex) in gridConfig.fields" :key="fieldIndex" class="px-2">
                    {{ fieldEntry.title || fieldEntry.key }}
                </th>
            </thead>
            <tr v-for="(rowData, rowIndex) in gridData" :key="rowIndex" :class="{ 'grid-dark-row': rowIndex % 2 }">
                <td v-for="(fieldEntry, fieldIndex) in gridConfig.fields" :key="fieldIndex" class="px-2 py-3">
                    <GridOperations
                        v-if="fieldEntry.type == 'operations'"
                        :title="rowData.title"
                        :operations="fieldEntry.operations"
                        @execute="executeOperation($event, rowData)" />
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
                        @tag-click="onTagClick" />
                </td>
            </tr>
        </table>
        <div class="flex-grow-1 h-100" />
        <div v-if="isAvailable" class="grid-footer">
            <b-pagination
                v-model="currentPage"
                :total-rows="totalRows"
                :per-page="perPage"
                size="sm"
                aria-controls="grid-table" />
        </div>
    </div>
</template>

<style lang="scss">
@import "theme/blue.scss";
@import "~bootstrap/scss/bootstrap.scss";

.grid-list {
    @extend .d-flex;
    @extend .flex-column;
    overflow: auto;
    .grid-footer {
        @extend .d-flex;
        @extend .grid-sticky;
        @extend .justify-content-center;
        @extend .pt-3;
        position: sticky;
        bottom: 0;
        .pagination {
            @extend .m-0;
        }
    }
    .grid-header {
        @extend .grid-sticky;
        @extend .pb-3;
        position: sticky;
        top: 0;
        h1 {
            @extend .m-0;
        }
    }
    .grid-sticky {
        z-index: 1;
        background: $white;
        opacity: 0.95;
    }
    .grid-dark-row {
        background: $gray-200;
    }
}
</style>
