import { type AnyHistoryEntry, getHistories } from "@/api/histories";
import { loadWorkflows, type WorkflowSummary } from "@/api/workflows";
import { useInvocationStore } from "@/stores/invocationStore";
import { useUserStore } from "@/stores/userStore";
import Filtering, { equals, isQuoted, type ValidFilter } from "@/utils/filtering";

import type { FieldFilter, FilterOption } from "./types";

/** Maximum number of workflows or histories a name resolves to, per lookup. */
export const NAME_MATCH_LIMIT = 50;

/** Number of most recently updated items a column filter lists before anything is typed. */
export const RECENT_LIMIT = 20;

/**
 * `workflow` and `history` match by name (substring, or exact when quoted) and are resolved to ids
 * through the workflow and history list APIs. `workflow_id` and `history_id` take comma-separated
 * ids; the column filters set those. Unkeyed text is a workflow name.
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
    workflow_id: { handler: equals("workflow_id", "workflow_id"), menuItem: false },
    history_id: { handler: equals("history_id", "history_id"), menuItem: false },
};

export const invocationsFiltering = new Filtering(validFilters, undefined, false, "workflow");

export interface InvocationFilterParams {
    workflow_id?: string[];
    history_id?: string[];
}

/**
 * Turn a name filter value into `name:` terms for the workflow/history index search: a quoted value
 * stays one exact-match term, an unquoted value becomes one substring term per word.
 */
export function nameSearch(value: string): string {
    if (isQuoted(value)) {
        return `name:${value}`;
    }
    return value
        .split(/\s+/)
        .filter((word) => word.length > 0)
        .map((word) => `name:${word}`)
        .join(" ");
}

function uniqueById<T extends { id: string }>(lists: T[][]): T[] {
    const byId = new Map<string, T>();
    for (const item of lists.flat()) {
        byId.set(item.id, item);
    }
    return [...byId.values()];
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
    return uniqueById(results.map(({ data }) => data));
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
    return uniqueById(results.map(({ data }) => data));
}

function splitIds(value: string): string[] {
    return value.split(",").filter((id) => id.length > 0);
}

/** Ids picked in a column filter, narrowed to the name matches when a name filter is set as well */
function combine(ids: string[] | undefined, matches: Array<{ id: string }> | undefined): string[] | undefined {
    if (!matches) {
        return ids;
    }
    const matchIds = matches.map((match) => match.id);
    return ids ? ids.filter((id) => matchIds.includes(id)) : matchIds;
}

/**
 * Translate the grid's filter text into `/api/invocations` query parameters, looking up names.
 * Returns `null` when the filters match no workflow or history, so no invocation can match.
 */
export async function resolveInvocationFilters(search: string): Promise<InvocationFilterParams | null> {
    const filters = Object.fromEntries(invocationsFiltering.getFiltersForText(search));
    const [workflows, histories] = await Promise.all([
        filters.workflow ? findWorkflowsByName(filters.workflow) : undefined,
        filters.history ? findHistoriesByName(filters.history) : undefined,
    ]);
    const params: InvocationFilterParams = {};
    const workflowIds = combine(filters.workflow_id ? splitIds(filters.workflow_id) : undefined, workflows);
    const historyIds = combine(filters.history_id ? splitIds(filters.history_id) : undefined, histories);
    if (workflowIds) {
        params.workflow_id = workflowIds;
    }
    if (historyIds) {
        params.history_id = historyIds;
    }
    const nothingMatched = params.workflow_id?.length === 0 || params.history_id?.length === 0;
    return nothingMatched ? null : params;
}

function plural(count: number, singular: string, pluralForm: string) {
    return `${count} ${count === 1 ? singular : pluralForm}`;
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
            const runText = typeof runs === "number" ? plural(runs, "run", "runs") : undefined;
            return [runText, ...notes].filter(Boolean).join(" · ") || undefined;
        },
    };
}

function historyOption(history: AnyHistoryEntry): FilterOption {
    const state = history.purged ? "purged" : history.deleted ? "deleted" : history.archived ? "archived" : undefined;
    const itemText = "count" in history ? plural(history.count, "item", "items") : undefined;
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
    plural: "histories",
    async search(query) {
        if (query) {
            return (await findHistoriesByName(query)).map(historyOption);
        }
        const { data } = await getHistories({ limit: RECENT_LIMIT, sortDesc: true });
        return data.map(historyOption);
    },
};
