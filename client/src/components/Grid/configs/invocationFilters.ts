import { uniqBy } from "lodash";

import { type AnyHistoryEntry, getHistories } from "@/api/histories";
import { loadWorkflows, type WorkflowSummary } from "@/api/workflows";
import { useInvocationStore } from "@/stores/invocationStore";
import { useUserStore } from "@/stores/userStore";
import Filtering, { equals, isQuoted, type ValidFilter } from "@/utils/filtering";
import { pluralize } from "@/utils/strings";

import type { FieldFilter, FilterOption } from "./types";

/** Maximum number of workflows or histories a name resolves to, per lookup. */
export const NAME_MATCH_LIMIT = 50;

/** Maximum number of ids `/api/invocations` accepts per filter. */
export const MAX_FILTER_IDS = 50;

/** Number of most recently updated items a column filter lists before anything is typed. */
export const RECENT_LIMIT = 20;

/**
 * `workflow` and `history` match by name (substring, or exact when quoted) and go to the server as
 * `search` terms. `workflow_id` and `history_id` can repeat, one id per term; the column filters
 * set those. Unkeyed text is a workflow name.
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
};

export const invocationsFiltering = new Filtering(validFilters, undefined, false, "workflow");

export interface InvocationFilterParams {
    workflow_id?: string[];
    history_id?: string[];
    search?: string;
}

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

/** Translate the grid's filter text into `/api/invocations` query parameters. */
export function invocationFilterParams(search: string): InvocationFilterParams {
    const filters = Object.fromEntries(invocationsFiltering.getFiltersForText(search)) as {
        workflow?: string;
        history?: string;
        workflow_id?: string[];
        history_id?: string[];
    };
    const params: InvocationFilterParams = {};
    if (filters.workflow_id) {
        params.workflow_id = filters.workflow_id.slice(0, MAX_FILTER_IDS);
    }
    if (filters.history_id) {
        params.history_id = filters.history_id.slice(0, MAX_FILTER_IDS);
    }
    const nameTerms = [
        filters.workflow && nameSearch(filters.workflow, "workflow"),
        filters.history && nameSearch(filters.history, "history"),
    ].filter(Boolean);
    if (nameTerms.length > 0) {
        params.search = nameTerms.join(" ");
    }
    return params;
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
