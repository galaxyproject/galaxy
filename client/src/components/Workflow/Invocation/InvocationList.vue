<script setup lang="ts">
import {
    faCheckCircle,
    faExclamationTriangle,
    faEye,
    faPlay,
    faPlus,
    faRedo,
    faShieldAlt,
    faSpinner,
    faStopCircle,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useElementSize } from "@vueuse/core";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { isRegisteredUser } from "@/api";
import type { WorkflowInvocation } from "@/api/invocations";
import type { StoredWorkflowDetailed } from "@/api/workflows";
import type { TableField } from "@/components/Common/GTable.types";
import {
    type AppliedTimeRange,
    getActiveTimeRange,
    setActiveTimeRange as applyTimeRangeFilter,
    type TimeRange,
} from "@/components/Common/timeRanges";
import { type ColumnFilterField, useColumnFilters } from "@/components/Grid/useColumnFilters";
import {
    historyColumnFilter,
    type INVOCATION_STATE_GROUPS,
    invocationFilterParams,
    invocationsFiltering,
    MAX_COLUMN_FILTER_PICKS,
    workflowColumnFilter,
} from "@/components/Workflow/Invocation/invocationFilters";
import { fetchInvocations, type InvocationsQuery } from "@/components/Workflow/Invocation/invocationsIndex";
import { useFilterTextValidation } from "@/composables/filterTextValidation";
import { useUserStore } from "@/stores/userStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import localize from "@/utils/localization";
import { withPrefix } from "@/utils/redirect";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GPagination from "@/components/BaseComponents/GPagination.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";
import GTable from "@/components/Common/GTable.vue";
import Heading from "@/components/Common/Heading.vue";
import LoadingOverlay from "@/components/Common/LoadingOverlay.vue";
import StatusGroupFilter, { type StatusGroup } from "@/components/Common/StatusGroupFilter.vue";
import TimeRangeFilter from "@/components/Common/TimeRangeFilter.vue";
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
/** Seconds the header message stays up */
const HEADER_MESSAGE_SECONDS = 5;
/** Narrower than this, the column filter chips get their own row under the filter bar */
const INLINE_CHIPS_MIN_WIDTH = 768;

/** The status buttons, one per `INVOCATION_STATE_GROUPS` key, in display order */
const STATUS_GROUPS = [
    { key: "active", label: "Active", icon: faSpinner, color: "yellow" },
    { key: "finished", label: "Finished", icon: faCheckCircle, color: "green" },
    { key: "problem", label: "Problem", icon: faExclamationTriangle, color: "red" },
    { key: "inactive", label: "Inactive", icon: faStopCircle, color: "grey" },
] as const satisfies (StatusGroup & { key: keyof typeof INVOCATION_STATE_GROUPS })[];

const DAY_MS = 24 * 60 * 60 * 1000;
/** The time range picks, as the Invoked time's `create_time` range */
const TIME_RANGES: TimeRange[] = [
    { key: "24h", label: "Last 24 hours", durationMs: DAY_MS },
    { key: "7d", label: "Last week", durationMs: 7 * DAY_MS },
    { key: "30d", label: "Last 30 days", durationMs: 30 * DAY_MS },
    { key: "90d", label: "Last 90 days", durationMs: 90 * DAY_MS },
];

interface Props {
    /** List every user's invocations that are still being scheduled, without search or column filters */
    admin?: boolean;
    /** Shown above the list when it opens, then hidden */
    headerMessage?: string;
    /** Shown when there are no invocations and no filters */
    noDataMessage?: string;
    /** List only the user's invocations in this history */
    historyId?: string;
    /** List only the user's invocations of this stored workflow */
    workflowId?: string;
    /** List exactly these invocations, as a batch run returns them, without paging or sorting */
    invocations?: WorkflowInvocation[];
}

const props = withDefaults(defineProps<Props>(), {
    admin: false,
    headerMessage: "",
    noDataMessage: "No Workflow Invocations to display",
    historyId: undefined,
    workflowId: undefined,
    invocations: undefined,
});

const router = useRouter();
const workflowStore = useWorkflowStore();
const { currentUser } = storeToRefs(useUserStore());

/** Scoped to one history or workflow: no heading, search or column filters, and Run in place of Rerun */
const scoped = !!(props.historyId || props.workflowId);
/** A batch run's invocations: no heading, filters, paging, sorting, Workflow or Run column */
const batch = !!props.invocations;
// the admin list covers every user, but the filter lookups only cover the admin's own workflows and histories
const filterable = !props.admin && !scoped && !batch;

const batchColumns: (ColumnFilterField & { sortable?: boolean })[] = [
    { key: "expand", title: null },
    { key: "view", title: "View" },
    { key: "history_id", title: "History" },
    { key: "create_time", title: "Invoked" },
    { key: "state", title: "State" },
];

const listColumns: (ColumnFilterField & { sortable?: boolean })[] = [
    { key: "expand", title: null },
    props.workflowId
        ? { key: "view", title: "View" }
        : { key: "workflow_id", title: "Workflow", filter: filterable ? workflowColumnFilter : undefined },
    ...(props.historyId
        ? []
        : [{ key: "history_id", title: "History", filter: filterable ? historyColumnFilter : undefined }]),
    { key: "create_time", title: "Invoked", sortable: true },
    { key: "state", title: "State" },
    { key: "execute", title: scoped ? "Run" : "Rerun" },
];
const columns = batch ? batchColumns : listColumns;
const fields: TableField[] = columns.map(({ key, title, sortable }) => ({ key, label: title ?? "", sortable }));

const listedInvocations = ref<WorkflowInvocation[]>([]);
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

const filterBar = ref<HTMLElement>();
const { width: filterBarWidth } = useElementSize(filterBar);
// the list's own width, since its panel can be narrow in a wide window
const narrowFilterBar = computed(() => filterBarWidth.value > 0 && filterBarWidth.value < INLINE_CHIPS_MIN_WIDTH);
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
    clearColumnFilters,
} = useColumnFilters(columns, invocationsFiltering, filterText, rawFilters, MAX_COLUMN_FILTER_PICKS);

/** The active `status` quick-filter value, or `undefined` if none is toggled on. */
const activeStatusFilter = computed(() => invocationsFiltering.getFilterValue(filterText.value, "status") || undefined);

/**
 * Toggles a `StatusGroupFilter` quick-filter button.
 *
 * Setting a `status` filter also clears any manually-picked `state`, since `disablesFilters` can't do
 * this for `status` the other way around (it's not a `FilterMenu` field, so no dropdown-change event
 * exists to trigger it from that side).
 */
function setActiveStatusFilter(group: string | undefined) {
    let newText = invocationsFiltering.applyFiltersToText({ state: "" }, filterText.value, true);
    newText = group
        ? invocationsFiltering.applyFiltersToText({ status: group }, newText)
        : invocationsFiltering.applyFiltersToText({ status: "" }, newText, true);
    filterText.value = newText;
}

/**
 * The range `setActiveTimeRange` itself last applied, so `activeTimeRange` can tell a quick-pick
 * range apart from a manually-entered `create_time` filter ("custom").
 */
let lastAppliedTimeRange: AppliedTimeRange | undefined;

/**
 * The active quick-pick time range, "custom" for a manually-entered `create_time` filter, or
 * `undefined` for "Anytime".
 */
const activeTimeRange = computed(() =>
    getActiveTimeRange(invocationsFiltering, "create_time", filterText.value, lastAppliedTimeRange),
);

/**
 * Sets or clears the `TimeRangeFilter` quick-pick, overloading the existing `create_time_gt`
 * filter instead of introducing a new one.
 */
function setActiveTimeRange(range: string | undefined) {
    const timeRange = TIME_RANGES.find(({ key }) => key === range);
    const result = applyTimeRangeFilter(invocationsFiltering, "create_time", filterText.value, timeRange);
    filterText.value = result.filterText;
    lastAppliedTimeRange = result.appliedRange;
}

const isAvailable = computed(() => !initDataLoading.value && totalRows.value > 0);
// column filters stay reachable when the current filters match nothing
const showTable = computed(
    () => !hasInvalidFilters.value && (isAvailable.value || (hasColumnFilters.value && !!filterText.value)),
);

// only the newest request may update the list
let latestRequest = 0;

async function load() {
    if (props.invocations) {
        listedInvocations.value = props.invocations;
        totalRows.value = props.invocations.length;
        initDataLoading.value = false;
        return;
    }
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
            // a workflow's list has always included its subworkflow invocations
            include_nested_invocations: props.workflowId ? undefined : false,
            ...(filterable ? invocationFilterParams(validatedFilterText()) : {}),
            history_id: props.historyId,
            workflow_id: props.workflowId,
        };
        if (props.admin) {
            query.include_terminal = false;
        } else if (isRegisteredUser(currentUser.value)) {
            query.user_id = currentUser.value.id;
        }
        // a scoped list already knows its history or workflow
        const [data, total] = await fetchInvocations(query, {
            histories: !props.historyId,
            workflows: !props.workflowId,
        });
        if (requestId === latestRequest) {
            collapseAll();
            listedInvocations.value = data;
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

function canRunAgain(invocation: WorkflowInvocation) {
    const workflow = workflowStore.getStoredWorkflowByInstanceId(
        invocation.workflow_id,
    ) as unknown as StoredWorkflowDetailed;
    return !workflow?.deleted;
}

/** Opens the invocation; a batch list opens it in a new tab, to keep the run's results page */
function viewInvocation(invocation: WorkflowInvocation) {
    if (batch) {
        window.open(withPrefix(`/workflows/invocations/${invocation.id}`), "_blank");
    } else {
        router.push(`/workflows/invocations/${invocation.id}`);
    }
}

/** Runs the invocation's workflow afresh; a workflow's list already knows its stored workflow */
function runWorkflow(invocation: WorkflowInvocation) {
    const storedWorkflowId = props.workflowId ?? workflowStore.getStoredWorkflowIdByInstanceId(invocation.workflow_id);
    router.push(`/workflows/run?id=${storedWorkflowId}`);
}

onMounted(load);

watch([currentPage, filterText, sortBy, sortDesc], load);
</script>

<template>
    <div v-if="isRegisteredUser(currentUser)" id="invocations-grid" class="d-flex flex-column h-100">
        <GAlert v-if="!!errorMessage" variant="danger" show>{{ errorMessage }}</GAlert>
        <GAlert v-if="props.headerMessage" variant="success" fade :show="HEADER_MESSAGE_SECONDS">
            {{ props.headerMessage }}
        </GAlert>
        <div v-if="!scoped && !batch" class="flex-shrink-0 mb-2">
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
                v-if="filterable"
                v-model:filter-text="filterText"
                v-model:show-advanced="showAdvanced"
                :name="TITLE"
                :placeholder="`search ${TITLE.toLowerCase()}`"
                :filter-class="invocationsFiltering"
                :loading="initDataLoading || resultsLoading"
                has-help
                view="compact">
                <template v-slot:menu-help-text>
                    <p>Text without a key matches workflow names. These filters can also be used:</p>
                    <dl>
                        <dt><code>workflow:____</code>, <code>history:____</code></dt>
                        <dd>
                            Workflow or history names containing the text. Quote it for an exact name, e.g.
                            <code>workflow:'RNA-seq'</code>.
                        </dd>
                        <dt><code>state:____</code></dt>
                        <dd>
                            Invocations in one state, e.g. <code>state:failed</code> or <code>state:scheduled</code>.
                        </dd>
                        <dt><code>create_time&gt;____</code>, <code>create_time&lt;____</code></dt>
                        <dd>
                            Invocations invoked after or before a date, e.g. <code>create_time&gt;2026-01-31</code>.
                        </dd>
                    </dl>
                    <GAlert variant="warning">
                        <strong>Note:</strong>
                        A <code>scheduled</code> invocation can still have jobs running, so it is listed as active.
                        Invocations run before Galaxy 26.0 may show as <code>scheduled</code> even if all their jobs
                        have finished.
                    </GAlert>
                </template>
            </FilterMenu>
            <div
                v-if="filterable && !showAdvanced"
                ref="filterBar"
                class="invocation-filter-bar d-flex align-items-center mt-2">
                <div>
                    <StatusGroupFilter
                        :groups="STATUS_GROUPS"
                        noun="invocations"
                        show-labels
                        :active-group="activeStatusFilter"
                        @update:active-group="setActiveStatusFilter" />
                </div>
                <GridColumnFilterChips
                    v-if="!narrowFilterBar"
                    class="invocation-filter-chips"
                    inline
                    :chips="activeColumnFilters"
                    @remove="removeColumnFilterOption"
                    @clear="clearColumnFilters" />
                <TimeRangeFilter
                    class="ml-auto"
                    :ranges="TIME_RANGES"
                    noun="invocations"
                    :active-range="activeTimeRange"
                    @update:active-range="setActiveTimeRange" />
            </div>
            <GridColumnFilterChips
                v-if="filterable && (showAdvanced || narrowFilterBar)"
                class="mt-2"
                :chips="activeColumnFilters"
                @remove="removeColumnFilterOption" />
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
                    <span v-else v-localize>{{ props.noDataMessage }}</span>
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
                :items="listedInvocations"
                :sort-by="sortBy"
                :sort-desc="sortDesc"
                :local-sorting="false"
                :overlay-loading="resultsLoading"
                @sort-changed="onSort">
                <template v-if="filterable" v-slot:head(workflow_id)="{ field }">
                    <span>{{ field.label }}</span>
                    <GridColumnFilter
                        :filter="workflowColumnFilter"
                        :title="field.label ?? field.key"
                        :selected="columnFilterSelection(workflowColumnFilter)"
                        :reached-limit="reachedColumnFilterLimit"
                        @update:selected="onColumnFilter(workflowColumnFilter, $event)" />
                </template>
                <template v-if="filterable" v-slot:head(history_id)="{ field }">
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
                <template v-slot:cell(view)="{ item }">
                    <GButton color="blue" :title="localize('View')" @click="viewInvocation(item)">
                        <FontAwesomeIcon :icon="faEye" />
                    </GButton>
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
                    <FontAwesomeIcon v-if="!canRunAgain(item)" :icon="faShieldAlt" />
                    <GButton v-else-if="scoped" color="blue" :title="localize('Run')" @click="runWorkflow(item)">
                        <FontAwesomeIcon :icon="faPlay" />
                    </GButton>
                    <GButton
                        v-else
                        color="blue"
                        :title="localize('Rerun')"
                        @click="router.push(`/workflows/rerun?invocation_id=${item.id}`)">
                        <FontAwesomeIcon :icon="faRedo" />
                    </GButton>
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
            <div v-if="isAvailable && !batch" class="d-flex justify-content-end pt-3">
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

// status buttons, then the column filter chips filling the space up to the time range
.invocation-filter-bar {
    gap: 0.5rem;

    .invocation-filter-chips {
        flex: 1 1 0;
        padding-left: 0.5rem;
        border-left: 1px solid var(--color-grey-300);
    }
}
</style>
