import { faHdd, faSitemap } from "@fortawesome/free-solid-svg-icons";
import { uniqBy } from "lodash";

import { type AnyHistoryEntry, getHistories } from "@/api/histories";
import type { InvocationState } from "@/api/invocations";
import { loadWorkflows, type WorkflowSummary } from "@/api/workflows";
import type { FieldFilter, FilterOption } from "@/components/Grid/configs/types";
import { useInvocationStore } from "@/stores/invocationStore";
import { useUserStore } from "@/stores/userStore";
import Filtering, { compare, equals, isQuoted, type ValidFilter } from "@/utils/filtering";
import { pluralize } from "@/utils/strings";

import type { InvocationsQuery } from "./invocationsIndex";

/** Maximum number of workflows or histories a name resolves to, per lookup. */
export const NAME_MATCH_LIMIT = 50;

/** Number of items that can be picked across the column filters; the server uses 10 search terms. */
export const MAX_COLUMN_FILTER_PICKS = 10;

/** Number of most recently updated items a column filter lists before anything is typed. */
export const RECENT_LIMIT = 20;

/** Every invocation state, for the `state` filter's dropdown. */
export const INVOCATION_STATES = [
    "new",
    "requires_materialization",
    "ready",
    "scheduled",
    "completed",
    "failed",
    "cancelling",
    "cancelled",
] as const satisfies readonly InvocationState[];

/**
 * Quick-toggle groups of invocation states for the status buttons; each state is in one group.
 * `scheduled` invocations can still have jobs running, so they are active.
 */
export const INVOCATION_STATE_GROUPS = {
    active: ["new", "requires_materialization", "ready", "scheduled"],
    finished: ["completed"],
    problem: ["failed"],
    inactive: ["cancelling", "cancelled"],
} as const satisfies Record<string, readonly InvocationState[]>;

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
        menuItem: true,
        disablesFilters: { status: null },
    },
    // set only by the status buttons; see `INVOCATION_STATE_GROUPS`
    status: {
        type: "Dropdown",
        handler: equals("status", "status"),
        datalist: Object.keys(INVOCATION_STATE_GROUPS),
        menuItem: false,
    },
    // the Invoked column; only its `create_time_gt` / `create_time_lt` range is sent to the server
    create_time: {
        placeholder: "invoked time",
        type: Date,
        handler: compare("create_time", "le"),
        isRangeInput: true,
        menuItem: true,
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

/** Translate the grid's filter text into the filter parameters of `/api/invocations`. */
export function invocationFilterParams(
    text: string,
): Pick<InvocationsQuery, "search" | "state" | "date_range_min" | "date_range_max"> {
    const value = (key: string) => invocationsFiltering.getFilterValue(text, key) || undefined;
    const status = value("status");
    const state = value("state");
    const states =
        status && status in INVOCATION_STATE_GROUPS
            ? [...INVOCATION_STATE_GROUPS[status as keyof typeof INVOCATION_STATE_GROUPS]]
            : state
              ? [state.toLowerCase() as InvocationState]
              : undefined;
    return {
        search: invocationSearch(text),
        state: states,
        date_range_min: value("create_time_gt"),
        date_range_max: value("create_time_lt"),
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
