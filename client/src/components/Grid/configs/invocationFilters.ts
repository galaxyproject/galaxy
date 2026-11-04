import { type AnyHistoryEntry, getHistories } from "@/api/histories";
import { loadWorkflows, type WorkflowSummary } from "@/api/workflows";
import Filtering, { equals, isQuoted, type ValidFilter } from "@/utils/filtering";

/** Maximum number of workflows or histories a name filter resolves to, per lookup. */
export const NAME_MATCH_LIMIT = 50;

/**
 * `workflow` and `history` match by name (substring, or exact when quoted) and are resolved to ids
 * through the workflow and history list APIs. `workflow_id` and `history_id` take an id directly;
 * the filter buttons in the grid set those. Unkeyed text is a workflow name.
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

export interface NameMatches<T> {
    /** The name filter value as typed */
    search: string;
    items: T[];
    /** A lookup returned more than `NAME_MATCH_LIMIT` matches, so only the first ones are used */
    truncated: boolean;
}

export interface InvocationFilterMatches {
    workflows?: NameMatches<WorkflowSummary>;
    histories?: NameMatches<AnyHistoryEntry>;
}

export interface ResolvedInvocationFilters {
    /** Query parameters for `/api/invocations`, `null` when a name filter matched nothing */
    params: { workflow_id?: string[]; history_id?: string[] } | null;
    matches: InvocationFilterMatches;
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

function collect<T extends { id: string }>(
    search: string,
    results: Array<{ items: T[]; total: number }>,
): NameMatches<T> {
    const byId = new Map<string, T>();
    for (const { items } of results) {
        for (const item of items) {
            byId.set(item.id, item);
        }
    }
    return {
        search,
        items: [...byId.values()],
        truncated: results.some(({ total }) => total > NAME_MATCH_LIMIT),
    };
}

/**
 * Invocations can reference the user's own visible, deleted and hidden workflows, and workflows
 * shared with or published by others. The index lists deleted and hidden workflows only on request,
 * one kind per call, so this takes three lookups.
 */
export async function findWorkflowsByName(name: string): Promise<NameMatches<WorkflowSummary>> {
    const search = nameSearch(name);
    const options = {
        sortBy: "update_time" as const,
        sortDesc: true,
        limit: NAME_MATCH_LIMIT,
        offset: 0,
        showPublished: false,
        skipStepCounts: true,
    };
    const results = await Promise.all([
        loadWorkflows({ ...options, filterText: search, showPublished: true }),
        loadWorkflows({ ...options, filterText: `${search} is:deleted` }),
        loadWorkflows({ ...options, filterText: search, showHidden: true }),
    ]);
    return collect(
        name,
        results.map(({ data, totalMatches }) => ({ items: data, total: totalMatches })),
    );
}

/**
 * Invocations live in the user's own histories: active and archived ones, plus deleted and purged
 * ones, which the index lists only when asked for with `is:deleted` / `is:purged`.
 */
export async function findHistoriesByName(name: string): Promise<NameMatches<AnyHistoryEntry>> {
    const search = nameSearch(name);
    const options = { limit: NAME_MATCH_LIMIT, sortDesc: true, showArchived: true };
    const results = await Promise.all([
        getHistories({ ...options, search }),
        getHistories({ ...options, search: `${search} is:deleted` }),
        getHistories({ ...options, search: `${search} is:purged` }),
    ]);
    return collect(
        name,
        results.map(({ data, total }) => ({ items: data, total })),
    );
}

/**
 * Translate the grid's filter text into `/api/invocations` query parameters, looking up names
 */
export async function resolveInvocationFilters(search: string): Promise<ResolvedInvocationFilters> {
    const filters = Object.fromEntries(invocationsFiltering.getFiltersForText(search));
    const matches: InvocationFilterMatches = {};
    const params: { workflow_id?: string[]; history_id?: string[] } = {};

    const [workflows, histories] = await Promise.all([
        !filters.workflow_id && filters.workflow ? findWorkflowsByName(filters.workflow) : undefined,
        !filters.history_id && filters.history ? findHistoriesByName(filters.history) : undefined,
    ]);

    if (filters.workflow_id) {
        params.workflow_id = [filters.workflow_id];
    } else if (workflows) {
        matches.workflows = workflows;
        params.workflow_id = workflows.items.map((workflow) => workflow.id);
    }
    if (filters.history_id) {
        params.history_id = [filters.history_id];
    } else if (histories) {
        matches.histories = histories;
        params.history_id = histories.items.map((history) => history.id);
    }

    const nothingMatched = params.workflow_id?.length === 0 || params.history_id?.length === 0;
    return { params: nothingMatched ? null : params, matches };
}
