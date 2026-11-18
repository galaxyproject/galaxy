import { faHdd, faSitemap } from "@fortawesome/free-solid-svg-icons";
import { uniqBy } from "lodash";

import { type AnyHistoryEntry, getHistories } from "@/api/histories";
import type { InvocationState } from "@/api/invocations";
import { loadWorkflows, type WorkflowSummary } from "@/api/workflows";
import type { TimeRange } from "@/components/Common/TimeRangeFilter.types";
import type { FieldFilter, FilterOption } from "@/components/Grid/configs/types";
import { useInvocationStore } from "@/stores/invocationStore";
import { useUserStore } from "@/stores/userStore";
import { isIsoDateTime, isoTimeAgo } from "@/utils/dates";
import Filtering, { compare, equals, isOneOf, isQuoted, type ValidFilter } from "@/utils/filtering";
import { pluralize } from "@/utils/strings";

import type { InvocationsQuery } from "./invocationsIndex";

/** Maximum number of workflows or histories a name resolves to, per lookup. */
export const NAME_MATCH_LIMIT = 50;

/** Number of items that can be picked across the column filters; the server uses 10 search terms. */
export const MAX_COLUMN_FILTER_PICKS = 10;

/** Number of most recently updated items a column filter lists before anything is typed. */
export const RECENT_LIMIT = 20;

/** The status buttons' groups of invocation states */
export type InvocationStateGroup = "active" | "finished" | "problem" | "inactive";

/**
 * Each invocation state's status group; a `Record` over every state, so a new state can't be left out.
 * `scheduled` invocations can still have jobs running, so they are active.
 */
export const INVOCATION_STATE_GROUP: Record<InvocationState, InvocationStateGroup> = {
    new: "active",
    requires_materialization: "active",
    ready: "active",
    scheduled: "active",
    completed: "finished",
    failed: "problem",
    cancelling: "inactive",
    cancelled: "inactive",
};

/** Every invocation state, for the `state` filter's dropdown. */
export const INVOCATION_STATES = Object.keys(INVOCATION_STATE_GROUP) as InvocationState[];

function statesIn(group: InvocationStateGroup) {
    return INVOCATION_STATES.filter((state) => INVOCATION_STATE_GROUP[state] === group);
}

/** The states in each status group, as the status buttons filter them */
export const INVOCATION_STATE_GROUPS: Record<InvocationStateGroup, InvocationState[]> = {
    active: statesIn("active"),
    finished: statesIn("finished"),
    problem: statesIn("problem"),
    inactive: statesIn("inactive"),
};

const DAY_MS = 24 * 60 * 60 * 1000;

/** The time range picker's quick picks for the Invoked time, each as an `invoked` filter value. */
export const INVOCATION_TIME_RANGES: TimeRange[] = [
    { key: "24h", label: "Last 24 hours", durationMs: DAY_MS },
    { key: "7d", label: "Last week", durationMs: 7 * DAY_MS },
    { key: "30d", label: "Last 30 days", durationMs: 30 * DAY_MS },
    { key: "90d", label: "Last 90 days", durationMs: 90 * DAY_MS },
];

/**
 * `workflow` and `history` match by name (substring, or exact when quoted). `workflow_id` and
 * `history_id` can repeat, one id per term; the column filters set those. Unkeyed text is a
 * workflow name. All of them go to the server as `search` terms.
 */
const validFilters: Record<string, ValidFilter<string>> = {
    workflow: {
        placeholder: "workflow name",
        type: String,
        handler: equals("workflow", "workflow"),
        menuItem: true,
    },
    history: {
        placeholder: "history name",
        type: String,
        handler: equals("history", "history"),
        menuItem: true,
    },
    workflow_id: { type: "MultiTags", handler: equals("workflow_id", "workflow_id"), menuItem: false },
    history_id: { type: "MultiTags", handler: equals("history_id", "history_id"), menuItem: false },
    state: {
        placeholder: "state",
        type: "Dropdown",
        handler: equals("state", "state"),
        datalist: [...INVOCATION_STATES],
        isValid: isOneOf(INVOCATION_STATES),
        menuItem: true,
        disablesFilters: { status: null },
    },
    // set only by the status buttons; see `INVOCATION_STATE_GROUPS`
    status: {
        type: "Dropdown",
        handler: equals("status", "status"),
        datalist: Object.keys(INVOCATION_STATE_GROUPS),
        isValid: isOneOf(Object.keys(INVOCATION_STATE_GROUPS)),
        menuItem: false,
    },
    // set only by the time range picker; see `INVOCATION_TIME_RANGES`
    invoked: {
        type: "Dropdown",
        handler: equals("invoked", "invoked"),
        datalist: INVOCATION_TIME_RANGES.map(({ key }) => key),
        isValid: isOneOf(INVOCATION_TIME_RANGES.map(({ key }) => key)),
        menuItem: false,
    },
    // the Invoked column, sent to the server as a range: `create_time_gt` / `create_time_lt`, or a plain date's whole day
    create_time: {
        placeholder: "invoked time",
        type: Date,
        handler: compare("create_time", "le"),
        isRangeInput: true,
        isValid: isIsoDateTime,
        menuItem: true,
        disablesFilters: { invoked: null },
    },
};

export const invocationsFiltering = new Filtering(validFilters, undefined, false, "workflow");

/**
 * Turn a name filter value into `key:` terms for a server search: a quoted value stays one
 * exact-match term, an unquoted value becomes one substring term per word.
 * Unquoted search terms only take word characters and hyphens, so other characters separate words.
 */
export function nameSearch(value: string, key = "name"): string {
    if (isQuoted(value)) {
        return `${key}:${value}`;
    }
    const words = value.split(/[^\p{L}\p{M}\p{N}_-]+/u).filter((word) => word.length > 0);
    return words.length > 0 ? words.map((word) => `${key}:${word}`).join(" ") : `${key}:'${value}'`;
}

const workflowListOptions = {
    sortBy: "update_time" as const,
    sortDesc: true,
    offset: 0,
    showPublished: false,
    skipStepCounts: true,
};

/**
 * Invocations can reference the user's own visible, deleted and hidden workflows, and workflows
 * shared with or published by others. The index lists deleted and hidden workflows only on request,
 * one kind per call. Own and shared workflows get their own lookup, so that recently updated
 * published workflows can't use up the limit.
 */
export async function findWorkflowsByName(name: string): Promise<WorkflowSummary[]> {
    const search = nameSearch(name);
    const options = { ...workflowListOptions, limit: NAME_MATCH_LIMIT };
    const results = await Promise.all([
        loadWorkflows({ ...options, filterText: search }),
        loadWorkflows({ ...options, filterText: search, showPublished: true }),
        loadWorkflows({ ...options, filterText: `${search} is:deleted` }),
        loadWorkflows({ ...options, filterText: search, showHidden: true }),
    ]);
    return uniqBy(
        results.flatMap(({ data }) => data),
        "id",
    );
}

/**
 * Invocations live in the user's own histories: active and archived ones, plus deleted and purged
 * ones, which the index lists only when asked for with `is:deleted` / `is:purged`.
 */
export async function findHistoriesByName(name: string): Promise<AnyHistoryEntry[]> {
    const search = nameSearch(name);
    const options = { limit: NAME_MATCH_LIMIT, sortDesc: true, showArchived: true };
    const results = await Promise.all([
        getHistories({ ...options, search }),
        getHistories({ ...options, search: `${search} is:deleted` }),
        getHistories({ ...options, search: `${search} is:purged` }),
    ]);
    return uniqBy(
        results.flatMap(({ data }) => data),
        "id",
    );
}

/** Translate the grid's filter text into the `search` parameter of `/api/invocations`. */
export function invocationSearch(text: string): string | undefined {
    const filters = Object.fromEntries(invocationsFiltering.getFiltersForText(text)) as {
        workflow?: string;
        history?: string;
        workflow_id?: string[];
        history_id?: string[];
    };
    const terms = [
        filters.workflow && nameSearch(filters.workflow, "workflow"),
        filters.history && nameSearch(filters.history, "history"),
        ...(filters.workflow_id ?? []).map((id) => `workflow_id:${id}`),
        ...(filters.history_id ?? []).map((id) => `history_id:${id}`),
    ].filter(Boolean);
    return terms.join(" ") || undefined;
}

/**
 * A typed date or time read in the user's time zone, as the list shows times, sent as a UTC timestamp.
 * A date without a time is that day's start, or with `endOfDay` its last moment.
 */
function userTime(value: string | undefined, endOfDay = false) {
    if (!value) {
        return undefined;
    }
    const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(value);
    const time = new Date(dateOnly ? `${value}T00:00` : value);
    // the filter's `isValid` already flags text that isn't a date
    if (Number.isNaN(time.getTime())) {
        return undefined;
    }
    if (dateOnly && endOfDay) {
        // the next day's start, less a millisecond
        time.setDate(time.getDate() + 1);
        time.setMilliseconds(-1);
    }
    return time.toISOString();
}

/** Translate the grid's filter text into the filter parameters of `/api/invocations`. */
export function invocationFilterParams(
    text: string,
): Pick<InvocationsQuery, "search" | "state" | "date_range_min" | "date_range_max"> {
    const value = (key: string) => invocationsFiltering.getFilterValue(text, key) || undefined;
    const status = value("status");
    const state = value("state");
    const states =
        status && Object.hasOwn(INVOCATION_STATE_GROUPS, status)
            ? [...INVOCATION_STATE_GROUPS[status as InvocationStateGroup]]
            : state
              ? [state.toLowerCase() as InvocationState]
              : undefined;
    // a plain `create_time:<date>` is that whole day
    const day = value("create_time")?.slice(0, 10);
    // a quick pick starts from now on every load, so its window slides; any typed time replaces it
    const typedTime = value("create_time") ?? value("create_time_gt") ?? value("create_time_lt");
    const range = typedTime ? undefined : INVOCATION_TIME_RANGES.find(({ key }) => key === value("invoked"));
    return {
        search: invocationSearch(text),
        state: states,
        date_range_min: userTime(value("create_time_gt") ?? day) ?? (range && isoTimeAgo(range.durationMs)),
        date_range_max: userTime(value("create_time_lt")) ?? userTime(day, true),
    };
}

function workflowOption(workflow: WorkflowSummary): FilterOption {
    const owned = useUserStore().matchesCurrentUsername(workflow.owner);
    const notes = [
        owned ? undefined : `by ${workflow.owner}`,
        workflow.deleted ? "deleted" : undefined,
        workflow.hidden ? "hidden" : undefined,
    ];
    return {
        id: workflow.id,
        name: workflow.name,
        updateTime: workflow.update_time,
        detail: () => {
            // /counts covers every user's runs, so only fetch it for the user's own workflows
            const runs = owned ? useInvocationStore().getInvocationCountByWorkflowId(workflow.id) : undefined;
            const runText = typeof runs === "number" ? `${runs} ${pluralize(runs, "run")}` : undefined;
            return [runText, ...notes].filter(Boolean).join(" · ") || undefined;
        },
    };
}

function historyOption(history: AnyHistoryEntry): FilterOption {
    const state = history.purged ? "purged" : history.deleted ? "deleted" : history.archived ? "archived" : undefined;
    const itemText = "count" in history ? `${history.count} ${pluralize(history.count, "item")}` : undefined;
    return {
        id: history.id,
        name: history.name,
        updateTime: history.update_time,
        detail: () => [itemText, state].filter(Boolean).join(" · ") || undefined,
    };
}

export const workflowColumnFilter: FieldFilter = {
    key: "workflow_id",
    clears: ["workflow"],
    icon: faSitemap,
    plural: "workflows",
    async search(query) {
        if (query) {
            return (await findWorkflowsByName(query)).map(workflowOption);
        }
        const { data } = await loadWorkflows({ ...workflowListOptions, filterText: "", limit: RECENT_LIMIT });
        return data.map(workflowOption);
    },
};

export const historyColumnFilter: FieldFilter = {
    key: "history_id",
    clears: ["history"],
    icon: faHdd,
    plural: "histories",
    async search(query) {
        if (query) {
            return (await findHistoriesByName(query)).map(historyOption);
        }
        const { data } = await getHistories({ limit: RECENT_LIMIT, sortDesc: true });
        return data.map(historyOption);
    },
};
