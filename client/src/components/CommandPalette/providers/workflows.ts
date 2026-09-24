import { faSitemap } from "@fortawesome/free-solid-svg-icons";

import type { WorkflowSummary } from "@/api/workflows";
import { useRecentPaletteItems } from "@/composables/useRecentPaletteItems";
import { useUserStore } from "@/stores/userStore";
import { useWorkflowStore, type WorkflowListVariant } from "@/stores/workflowStore";
import { relativeUpdatedLabel } from "@/utils/dates";

import type {
    CommandPaletteProvider,
    PaletteContext,
    PaletteItem,
    PaletteSearchOptions,
    ScopedSection,
} from "../types";
import { dedupePaletteItemsByEntity, rankPaletteItems } from "../utilities";
import { fetchOrFail } from "./errors";
import { PALETTE_LIMITS } from "./limits";
import { markListRefreshed, refreshListWhenStale } from "./refresh";
import type { ScopeDefinition } from "./scopes";

/** Entity type this provider records in the palette MRU (`useRecentPaletteItems`) */
export const WORKFLOW_RECENT_TYPE = "workflow";

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

/**
 * One result row. Enter runs the workflow; workflows the current user owns
 * additionally offer their editor on shift+enter.
 */
function workflowItem(workflow: WorkflowSummary, sectionId: string): PaletteItem {
    const userStore = useUserStore();
    const owned = userStore.matchesCurrentUsername(workflow.owner);
    // the owner is only worth a line for workflows that are not the user's own
    const subtitle = [
        owned ? undefined : workflow.owner && `by ${workflow.owner}`,
        relativeUpdatedLabel(workflow.update_time),
    ]
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

/** A failing background fetch degrades to whatever the store already holds */
async function fetchQuietly<T>(fetch: () => Promise<T>): Promise<T | undefined> {
    try {
        return await fetch();
    } catch (error) {
        console.debug("Command palette could not fetch workflows", error);
        return undefined;
    }
}

/** How far a section may go to fill itself */
interface ListOptions {
    /**
     * Never issue a request, not even to hydrate an empty cache. The root
     * fan-out passes it for the user's own workflows, which it filters locally;
     * the shared and published lists it does search, see {@link variantItems}.
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
            // nothing cached to fall back on, so a failure is reported
            await fetchOrFail(() => workflowStore.fetchWorkflowList(variant, "", { limit: PALETTE_LIMITS.page }));
            markListRefreshed(refreshKey);
        } else {
            // stale-while-revalidate: the cached rows render now, the refreshed
            // ones land in the store for the next keystroke
            refreshListWhenStale(refreshKey, () =>
                workflowStore.fetchWorkflowList(variant, "", { limit: PALETTE_LIMITS.page }),
            );
        }
    }
    const cached = workflowStore.getWorkflowList(variant);
    const local = rankPaletteItems(
        latestFirst(cached).map((workflow) => workflowItem(workflow, variant)),
        query,
    );
    const cacheIsComplete = cached.length < PALETTE_LIMITS.page;
    if (cacheOnly || !query || !queryBackend || cacheIsComplete || local.length >= limit) {
        return local.slice(0, limit);
    }
    await fetchQuietly(() => workflowStore.fetchWorkflowList(variant, query, { limit: PALETTE_LIMITS.page }));
    const remote = workflowStore.getWorkflowList(variant, query).map((workflow) => workflowItem(workflow, variant));
    // the backend over-matches short searches (`search=zqx` comes back with the
    // whole list), so the merged rows are ranked locally just like the cache is
    return rankPaletteItems(dedupePaletteItemsByEntity([...local, ...remote]), query).slice(0, limit);
}

/** The lists the root fan-out searches on the backend, next to the own cache */
function rootVariants(isAnonymous: boolean): WorkflowListVariant[] {
    // an anonymous visitor has neither own nor shared-with-me workflows
    return isAnonymous ? ["published"] : ["shared", "published"];
}

/**
 * One backend search for the root fan-out. The store keys its lists by variant
 * and query, so the fetched rows are the matches for this query alone; a failing
 * variant contributes nothing rather than costing the whole section.
 *
 * A whole page is fetched even though only `PALETTE_LIMITS.rootListing` rows are
 * shown: the backend matches loosely and orders by update time, so the newest
 * few rows it answers with are often ranked away here, and asking for exactly as
 * many rows as the section renders would leave it empty. The extra rows cost
 * nothing beyond the one request the variant already makes.
 */
async function variantItems(variant: WorkflowListVariant, query: string): Promise<PaletteItem[]> {
    const workflowStore = useWorkflowStore();
    const workflows =
        (await fetchQuietly(() => workflowStore.fetchWorkflowList(variant, query, { limit: PALETTE_LIMITS.page }))) ??
        [];
    return rankPaletteItems(
        workflows.map((workflow) => workflowItem(workflow, variant)),
        query,
    ).slice(0, PALETTE_LIMITS.rootListing);
}

/**
 * Root mode results: the cached own workflows answer the keystroke instantly,
 * while the shared and published lists are searched on the backend — the
 * palette is the one place that finds a workflow without being told where it
 * lives. Copies of one workflow collapse into the own row, which knows about
 * its editor; the palette's debounce keeps the request volume down.
 */
async function rootItems(query: string, isAnonymous: boolean, localOnly = false): Promise<PaletteItem[]> {
    // the searches start before the cache is filtered, so they run in parallel
    const listed = Promise.all(
        (localOnly ? [] : rootVariants(isAnonymous)).map((variant) => variantItems(variant, query)),
    );
    const own = isAnonymous ? [] : await listItems("my", query, PALETTE_LIMITS.rootOwn, { cacheOnly: true });
    const merged = dedupePaletteItemsByEntity([own, ...(await listed)].flat());
    return rankPaletteItems(merged, query).slice(0, PALETTE_LIMITS.rootOwn + PALETTE_LIMITS.rootListing);
}

/** Workflows opened through the palette before, most recently used first */
function recentItems(query: string, limit = PALETTE_LIMITS.recent): PaletteItem[] {
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
export function myWorkflowItems(query: string, limit = PALETTE_LIMITS.section): Promise<PaletteItem[]> {
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
        return recentItems("", PALETTE_LIMITS.rootOwn);
    },
    /** Root mode fan-out over the cached own list and the public ones */
    async search(query: string, ctx: PaletteContext, options: PaletteSearchOptions = {}) {
        if (query.length < PALETTE_LIMITS.minBackendQuery) {
            return [];
        }
        return rootItems(query, ctx.isAnonymous, options.localOnly);
    },
    /**
     * `w:` shows bookmarks, palette recents and the user's latest workflows;
     * `ws:`/`wp:` show the shared/published list alone. The palette recents are
     * one list per entity type rather than per scope, so they are only offered
     * by the base scope — a private workflow has no business showing up under
     * "shared" or "public". The query filters every section.
     */
    async searchScoped(scope: ScopeDefinition, query: string) {
        const variant = listVariant(scope.variant);
        const [bookmarked, results] = await Promise.all([
            variant === "my" ? listItems("bookmarked", query, PALETTE_LIMITS.recent, { queryBackend: false }) : [],
            listItems(variant, query, PALETTE_LIMITS.section),
        ]);
        return [
            ...section("bookmarked", "Bookmarked", bookmarked),
            ...section("recent", "Recent", variant === "my" ? recentItems(query) : []),
            ...section(variant, resultsTitle(scope, query), results),
        ];
    },
};
