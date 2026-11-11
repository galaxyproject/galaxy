<script setup lang="ts">
import { faPlus, faRedo, faShieldAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { isRegisteredUser } from "@/api";
import type { WorkflowInvocation } from "@/api/invocations";
import type { StoredWorkflowDetailed } from "@/api/workflows";
import type { TableField } from "@/components/Common/GTable.types";
import {
    historyColumnFilter,
    invocationSearch,
    invocationsFiltering,
    MAX_COLUMN_FILTER_PICKS,
    workflowColumnFilter,
} from "@/components/Grid/configs/invocationFilters";
import { fetchInvocations, type InvocationsQuery } from "@/components/Grid/configs/invocationsIndex";
import { type ColumnFilterField, useColumnFilters } from "@/components/Grid/useColumnFilters";
import { useFilterTextValidation } from "@/composables/filterTextValidation";
import { useUserStore } from "@/stores/userStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import localize from "@/utils/localization";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GPagination from "@/components/BaseComponents/GPagination.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";
import GTable from "@/components/Common/GTable.vue";
import Heading from "@/components/Common/Heading.vue";
import LoadingOverlay from "@/components/Common/LoadingOverlay.vue";
import GridColumnFilter from "@/components/Grid/GridColumnFilter.vue";
import GridColumnFilterChips from "@/components/Grid/GridColumnFilterChips.vue";
import GridExpand from "@/components/Grid/GridElements/GridExpand.vue";
import GridLink from "@/components/Grid/GridElements/GridLink.vue";
import HelpText from "@/components/Help/HelpText.vue";
import SwitchToHistoryLink from "@/components/History/SwitchToHistoryLink.vue";
import UtcDate from "@/components/UtcDate.vue";
import WorkflowInvocationState from "@/components/WorkflowInvocationState/WorkflowInvocationState.vue";

const LIMIT = 25;
const TITLE = "Workflow Invocations";

const router = useRouter();
const workflowStore = useWorkflowStore();
const { currentUser } = storeToRefs(useUserStore());

const columns: (ColumnFilterField & { sortable?: boolean })[] = [
    { key: "expand", title: null },
    { key: "workflow_id", title: "Workflow", filter: workflowColumnFilter },
    { key: "history_id", title: "History", filter: historyColumnFilter },
    { key: "create_time", title: "Invoked", sortable: true },
    { key: "state", title: "State" },
    { key: "execute", title: "Rerun" },
];
const fields: TableField[] = columns.map(({ key, title, sortable }) => ({ key, label: title ?? "", sortable }));

const invocations = ref<WorkflowInvocation[]>([]);
const totalRows = ref(0);
const currentPage = ref(1);
const sortBy = ref("create_time");
const sortDesc = ref(true);
const errorMessage = ref("");
const initDataLoading = ref(true);
const resultsLoading = ref(false);

// GTable tracks expanded rows by index, so expanded rows are collapsed before new rows load
const expandedIds = ref(new Set<string>());
const expandedToggles = new Map<string, () => void>();

const filterText = ref("");
const showAdvanced = ref(false);
const { rawFilters, invalidFilters, hasInvalidFilters, validatedFilterText } = useFilterTextValidation(
    invocationsFiltering,
    filterText,
    false,
);
const {
    hasColumnFilters,
    columnFilterSelection,
    activeColumnFilters,
    reachedColumnFilterLimit,
    onColumnFilter,
    removeColumnFilterOption,
} = useColumnFilters(columns, invocationsFiltering, filterText, rawFilters, MAX_COLUMN_FILTER_PICKS);

const isAvailable = computed(() => !initDataLoading.value && totalRows.value > 0);
// column filters stay reachable when the current filters match nothing
const showTable = computed(
    () => !hasInvalidFilters.value && (isAvailable.value || (hasColumnFilters.value && !!filterText.value)),
);

// only the newest request may update the list
let latestRequest = 0;

async function load() {
    const requestId = ++latestRequest;
    resultsLoading.value = true;
    if (hasInvalidFilters.value) {
        initDataLoading.value = false;
        resultsLoading.value = false;
        return;
    }
    try {
        const query: InvocationsQuery = {
            limit: LIMIT,
            offset: LIMIT * (currentPage.value - 1),
            sort_by: sortBy.value as InvocationsQuery["sort_by"],
            sort_desc: sortDesc.value,
            include_nested_invocations: false,
            search: invocationSearch(validatedFilterText()),
        };
        if (isRegisteredUser(currentUser.value)) {
            query.user_id = currentUser.value.id;
        }
        const [data, total] = await fetchInvocations(query);
        if (requestId === latestRequest) {
            collapseAll();
            invocations.value = data;
            totalRows.value = total;
            errorMessage.value = "";
        }
    } catch (e) {
        if (requestId === latestRequest) {
            errorMessage.value = `Failed to obtain grid data: ${e}`;
        }
    } finally {
        if (requestId === latestRequest) {
            initDataLoading.value = false;
            resultsLoading.value = false;
        }
    }
}

function onSort(newSortBy: string, newSortDesc: boolean) {
    sortBy.value = newSortBy;
    sortDesc.value = newSortDesc;
}

function onShowDetails(invocation: WorkflowInvocation, toggleDetails: () => void) {
    const ids = new Set(expandedIds.value);
    if (ids.has(invocation.id)) {
        ids.delete(invocation.id);
        expandedToggles.delete(invocation.id);
    } else {
        ids.add(invocation.id);
        expandedToggles.set(invocation.id, toggleDetails);
    }
    expandedIds.value = ids;
    toggleDetails();
}

function collapseAll() {
    expandedToggles.forEach((toggleDetails) => toggleDetails());
    expandedToggles.clear();
    expandedIds.value = new Set();
}

function canRerun(invocation: WorkflowInvocation) {
    const workflow = workflowStore.getStoredWorkflowByInstanceId(
        invocation.workflow_id,
    ) as unknown as StoredWorkflowDetailed;
    return !workflow?.deleted;
}

onMounted(load);

watch([currentPage, filterText, sortBy, sortDesc], load);
</script>

<template>
    <div v-if="isRegisteredUser(currentUser)" id="invocations-grid" class="d-flex flex-column h-100">
        <GAlert v-if="!!errorMessage" variant="danger" show>{{ errorMessage }}</GAlert>
        <div class="flex-shrink-0 mb-2">
            <BreadcrumbHeading :items="[{ title: TITLE }]">
                <GButton
                    size="small"
                    color="blue"
                    outline
                    data-description="grid action import invocation"
                    @click="router.push('/workflows/invocations/import')">
                    <FontAwesomeIcon :icon="faPlus" />
                    <span v-localize>Import Invocation</span>
                </GButton>
            </BreadcrumbHeading>
            <FilterMenu
                v-model:filter-text="filterText"
                v-model:show-advanced="showAdvanced"
                :name="TITLE"
                :placeholder="`search ${TITLE.toLowerCase()}`"
                :filter-class="invocationsFiltering"
                :loading="initDataLoading || resultsLoading"
                view="compact" />
            <GridColumnFilterChips :chips="activeColumnFilters" @remove="removeColumnFilterOption" />
        </div>

        <div class="invocation-list-content flex-grow-1 overflow-auto">
            <div v-if="initDataLoading" class="position-relative h-100" data-description="grid initial loading">
                <LoadingOverlay />
            </div>
            <span v-if="!initDataLoading && (!isAvailable || hasInvalidFilters)">
                <GAlert v-if="!hasInvalidFilters" variant="info" show>
                    <span v-if="filterText">
                        <span v-localize>Nothing found with:</span>
                        <b>{{ filterText }}</b>
                    </span>
                    <span v-else v-localize>No Workflow Invocations to display</span>
                </GAlert>
                <GAlert v-else-if="invalidFilters" variant="danger" show>
                    <Heading h4 inline size="sm" class="flex-grow-1 mb-2">Invalid filters in query:</Heading>
                    <ul>
                        <li v-for="[invalidKey, value] in Object.entries(invalidFilters)" :key="invalidKey">
                            <b>{{ invalidKey }}</b>
                            : {{ value }}
                        </li>
                    </ul>
                    <a href="javascript:void(0)" class="ui-link" @click="filterText = validatedFilterText()">
                        Remove invalid filters from query
                    </a>
                    or
                    <a
                        v-g-tooltip.hover
                        title="Note that this might produce inaccurate results"
                        href="javascript:void(0)"
                        class="ui-link"
                        @click="filterText = `'${filterText}'`">
                        Match the exact query provided
                    </a>
                </GAlert>
            </span>

            <GTable
                v-if="!initDataLoading && showTable"
                id="invocations-table"
                :fields="fields"
                :items="invocations"
                :sort-by="sortBy"
                :sort-desc="sortDesc"
                :local-sorting="false"
                :overlay-loading="resultsLoading"
                @sort-changed="onSort">
                <template v-slot:head(workflow_id)="{ field }">
                    <span>{{ field.label }}</span>
                    <GridColumnFilter
                        :filter="workflowColumnFilter"
                        :title="field.label ?? field.key"
                        :selected="columnFilterSelection(workflowColumnFilter)"
                        :reached-limit="reachedColumnFilterLimit"
                        @update:selected="onColumnFilter(workflowColumnFilter, $event)" />
                </template>
                <template v-slot:head(history_id)="{ field }">
                    <span>{{ field.label }}</span>
                    <GridColumnFilter
                        :filter="historyColumnFilter"
                        :title="field.label ?? field.key"
                        :selected="columnFilterSelection(historyColumnFilter)"
                        :reached-limit="reachedColumnFilterLimit"
                        @update:selected="onColumnFilter(historyColumnFilter, $event)" />
                </template>

                <template v-slot:cell(expand)="{ item, toggleDetails }">
                    <GridExpand
                        :details-showing="expandedIds.has(item.id)"
                        @show-details="onShowDetails(item, toggleDetails)" />
                </template>
                <template v-slot:cell(workflow_id)="{ item }">
                    <GridLink
                        :text="workflowStore.getStoredWorkflowNameByInstanceId(item.workflow_id)"
                        @click="router.push(`/workflows/invocations/${item.id}`)" />
                </template>
                <template v-slot:cell(history_id)="{ item }">
                    <span v-if="!item.history_id" v-localize> No history found </span>
                    <SwitchToHistoryLink v-else :history-id="item.history_id" />
                </template>
                <template v-slot:cell(create_time)="{ item }">
                    <UtcDate :date="item.create_time" mode="elapsed" />
                </template>
                <template v-slot:cell(state)="{ item }">
                    <HelpText :uri="`galaxy.invocations.states.${item.state}`" :text="item.state" />
                </template>
                <template v-slot:cell(execute)="{ item }">
                    <GButton
                        v-if="canRerun(item)"
                        color="blue"
                        :title="localize('Rerun')"
                        @click="router.push(`/workflows/rerun?invocation_id=${item.id}`)">
                        <FontAwesomeIcon :icon="faRedo" />
                    </GButton>
                    <FontAwesomeIcon v-else :icon="faShieldAlt" />
                </template>

                <template v-slot:row-details="{ item }">
                    <div class="card p-2" data-description="grid expanded row">
                        <span class="mb-2" :data-invocation-id="item.id">
                            <small>
                                <b>Last updated: <UtcDate :date="item.update_time" mode="elapsed" />; Invocation ID:</b>
                            </small>
                            <code>{{ item.id }}</code>
                        </span>
                        <WorkflowInvocationState :invocation-id="item.id" />
                    </div>
                </template>
            </GTable>
        </div>

        <div class="flex-shrink-0">
            <div v-if="isAvailable" class="d-flex justify-content-end pt-3">
                <GPagination
                    v-model="currentPage"
                    :total-rows="totalRows"
                    :per-page="LIMIT"
                    size="small"
                    data-description="invocation list pager" />
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
// only the list scrolls; the header and pager stay put
.invocation-list-content {
    min-height: 0;
}
</style>
