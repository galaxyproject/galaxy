import { faSitemap } from "@fortawesome/free-solid-svg-icons";
import { formatDistanceToNow } from "date-fns";

import type { WorkflowSummary } from "@/api/workflows";
import { useRecentPaletteItems } from "@/composables/useRecentPaletteItems";
import { useUserStore } from "@/stores/userStore";
import { useWorkflowStore, type WorkflowListVariant } from "@/stores/workflowStore";
import { galaxyTimeToDate } from "@/utils/dates";

import type { CommandPaletteProvider, PaletteContext, PaletteItem, ScopedSection } from "../types";
import { rankPaletteItems } from "../utilities";
import { markListRefreshed, refreshListWhenStale } from "./refresh";
import type { ScopeDefinition } from "./scopes";

/** Entity type this provider records in the palette MRU (`useRecentPaletteItems`) */
export const WORKFLOW_RECENT_TYPE = "workflow";

/** Per section caps, kept small so several sections fit without scrolling */
const RESULTS_LIMIT = 8;
const BOOKMARKED_LIMIT = 5;
const RECENT_LIMIT = 5;
const ROOT_LIMIT = 5;

/** Unscoped search only joins the fan-out once the query is specific enough */
const MIN_ROOT_QUERY_LENGTH = 2;

/**
 * How many entries one cached list holds. A list that came back shorter than a
 * full page is everything the backend has for it, so the cache can answer any
 * query on its own and no search request is needed.
 */
const LIST_PAGE_SIZE = 25;

/** Scope variant (`undefined` | `shared` | `published`) to store list variant */
function listVariant(variant?: string): WorkflowListVariant {
    switch (variant) {
        case "shared":
            return "shared";
        case "published":
            return "published";
        default:
            return "my";
    }
}

function runUrl(workflowId: string): string {
    return `/workflows/run?id=${workflowId}`;
}

function editUrl(workflowId: string): string {
    return `/workflows/edit?id=${workflowId}`;
}

/** Section scoped item id, so the same workflow may appear in several sections */
function itemId(sectionId: string, workflowId: string): string {
    return `workflows:${sectionId}:${workflowId}`;
}

function updatedLabel(updateTime?: string): string | undefined {
    if (!updateTime) {
        return undefined;
    }
    try {
        return `updated ${formatDistanceToNow(galaxyTimeToDate(updateTime), { addSuffix: true })}`;
    } catch {
        // a malformed timestamp must not cost the user the whole result row
        return undefined;
    }
}

/**
 * One result row. Enter runs the workflow; workflows the current user owns
 * additionally offer their editor on shift+enter.
 */
function workflowItem(workflow: WorkflowSummary, sectionId: string): PaletteItem {
    const userStore = useUserStore();
    const owned = userStore.matchesCurrentUsername(workflow.owner);
    // the owner is only worth a line for workflows that are not the user's own
    const subtitle = [owned ? undefined : workflow.owner && `by ${workflow.owner}`, updatedLabel(workflow.update_time)]
        .filter(Boolean)
        .join(" · ");
    return {
        id: itemId(sectionId, workflow.id),
        icon: faSitemap,
        keywords: [workflow.owner, ...(workflow.tags ?? [])].filter(Boolean).join(" "),
        mru: { type: WORKFLOW_RECENT_TYPE, id: workflow.id },
        title: workflow.name,
        to: runUrl(workflow.id),
        ...(subtitle ? { subtitle } : {}),
        ...(owned ? { secondaryAction: { label: "Edit workflow", to: editUrl(workflow.id) } } : {}),
    };
}

/** Newest first, so an empty query renders the "Latest" section as promised */
function latestFirst(workflows: WorkflowSummary[]): WorkflowSummary[] {
    return [...workflows].sort((a, b) => (b.update_time ?? "").localeCompare(a.update_time ?? ""));
}

function dedupeById(items: PaletteItem[]): PaletteItem[] {
    const seen = new Set<string>();
    const unique: PaletteItem[] = [];
    items.forEach((item) => {
        if (!seen.has(item.id)) {
            seen.add(item.id);
            unique.push(item);
        }
    });
    return unique;
}

/** A failing background fetch degrades to whatever the store already holds */
async function fetchQuietly(fetch: () => Promise<unknown>) {
    try {
        await fetch();
    } catch (error) {
        console.debug("Command palette could not fetch workflows", error);
    }
}

/** How far a section may go to fill itself */
interface ListOptions {
    /**
     * Never issue a request, not even to hydrate an empty cache. The unscoped
     * root fan-out runs on every provider at once, so it only ever filters what
     * the stores already hold; the scopes do the fetching.
     */
    cacheOnly?: boolean;
    /** Whether a query the cache cannot answer may trigger a search request */
    queryBackend?: boolean;
}

/**
 * Store first section data: the cached list answers every keystroke locally and
 * the backend is only asked when the cache is empty, or when an incomplete
 * cache cannot fill the section for the current query. Backend results are
 * merged into the store by {@link useWorkflowStore} and deduplicated by id here.
 *
 * @param variant which cached list to read
 * @param query free text filter, already trimmed
 * @param limit section cap
 * @param options fetching budget, see {@link ListOptions}
 */
async function listItems(
    variant: WorkflowListVariant,
    query: string,
    limit: number,
    options: ListOptions = {},
): Promise<PaletteItem[]> {
    const { cacheOnly = false, queryBackend = true } = options;
    const workflowStore = useWorkflowStore();
    const refreshKey = `workflows:${variant}`;
    if (!cacheOnly) {
        if (!workflowStore.isWorkflowListLoaded(variant)) {
            await fetchQuietly(() => workflowStore.fetchWorkflowList(variant, "", { limit: LIST_PAGE_SIZE }));
            markListRefreshed(refreshKey);
        } else {
            // stale-while-revalidate: the cached rows render now, the refreshed
            // ones land in the store for the next keystroke
            refreshListWhenStale(refreshKey, () =>
                workflowStore.fetchWorkflowList(variant, "", { limit: LIST_PAGE_SIZE }),
            );
        }
    }
    const cached = workflowStore.getWorkflowList(variant);
    const local = rankPaletteItems(
        latestFirst(cached).map((workflow) => workflowItem(workflow, variant)),
        query,
    );
    const cacheIsComplete = cached.length < LIST_PAGE_SIZE;
    if (cacheOnly || !query || !queryBackend || cacheIsComplete || local.length >= limit) {
        return local.slice(0, limit);
    }
    await fetchQuietly(() => workflowStore.fetchWorkflowList(variant, query, { limit: LIST_PAGE_SIZE }));
    const remote = workflowStore.getWorkflowList(variant, query).map((workflow) => workflowItem(workflow, variant));
    return dedupeById([...local, ...remote]).slice(0, limit);
}

/** Workflows opened through the palette before, most recently used first */
function recentItems(query: string, limit = RECENT_LIMIT): PaletteItem[] {
    const workflowStore = useWorkflowStore();
    const { recentItems: recentEntries } = useRecentPaletteItems();
    const items = recentEntries(WORKFLOW_RECENT_TYPE).map((entry) => {
        const summary = workflowStore.getWorkflowSummaryById(entry.id);
        return summary
            ? workflowItem(summary, "recent")
            : {
                  id: itemId("recent", entry.id),
                  icon: faSitemap,
                  mru: { type: WORKFLOW_RECENT_TYPE, id: entry.id },
                  title: entry.name,
                  to: entry.to ?? runUrl(entry.id),
              };
    });
    return rankPaletteItems(items, query).slice(0, limit);
}

/**
 * The user's own workflows as run rows, store first like the `w:` scope. Used by
 * the "Run workflow" action, which collects its workflow as an argument.
 */
export function myWorkflowItems(query: string, limit = RESULTS_LIMIT): Promise<PaletteItem[]> {
    return listItems("my", query.trim(), limit);
}

function resultsTitle(scope: ScopeDefinition, query: string): string {
    if (!query) {
        return "Latest";
    }
    return scope.variant ? scope.label : "Workflows";
}

function section(id: string, title: string, items: PaletteItem[]): ScopedSection[] {
    return items.length ? [{ id, items, title }] : [];
}

export const workflowsProvider: CommandPaletteProvider = {
    id: "workflows",
    title: "Workflows",
    /** Root mode: workflows the palette remembers, no request needed */
    emptyQueryItems(ctx: PaletteContext) {
        if (ctx.isAnonymous) {
            return [];
        }
        return recentItems("", ROOT_LIMIT);
    },
    /** Root mode fan-out, filtering the cached own list without any request */
    async search(query: string, ctx: PaletteContext) {
        const trimmed = query.trim();
        if (ctx.isAnonymous || trimmed.length < MIN_ROOT_QUERY_LENGTH) {
            return [];
        }
        return listItems("my", trimmed, ROOT_LIMIT, { cacheOnly: true });
    },
    /**
     * `w:` shows bookmarks, palette recents and the user's latest workflows;
     * `ws:`/`wp:` show recents and the shared/published list. The query filters
     * every section.
     */
    async searchScoped(scope: ScopeDefinition, query: string) {
        const variant = listVariant(scope.variant);
        const trimmed = query.trim();
        const [bookmarked, results] = await Promise.all([
            variant === "my" ? listItems("bookmarked", trimmed, BOOKMARKED_LIMIT, { queryBackend: false }) : [],
            listItems(variant, trimmed, RESULTS_LIMIT),
        ]);
        return [
            ...section("bookmarked", "Bookmarked", bookmarked),
            ...section("recent", "Recent", recentItems(trimmed)),
            ...section(variant, resultsTitle(scope, trimmed), results),
        ];
    },
};
