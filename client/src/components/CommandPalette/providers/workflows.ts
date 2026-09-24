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
import { rankPaletteItems } from "../utilities";
import { PALETTE_LIMITS } from "./limits";
import type { ScopeDefinition } from "./scopes";
import { type ListingSearch, rootListItems, storeFirstItems, type StoreFirstList } from "./storeFirst";

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

/** Rows of one cached list, newest first so an empty query renders "Latest" as promised */
function workflowRows(workflows: WorkflowSummary[], variant: WorkflowListVariant): PaletteItem[] {
    return [...workflows]
        .sort((a, b) => (b.update_time ?? "").localeCompare(a.update_time ?? ""))
        .map((workflow) => workflowItem(workflow, variant));
}

/**
 * One workflow list, store first. The store keeps the rows of each query apart
 * from the listing, so a search is read back from its own list; the bookmarks
 * are only ever filtered locally.
 */
function workflowList(variant: WorkflowListVariant): StoreFirstList {
    const workflowStore = useWorkflowStore();
    return {
        key: `workflows:${variant}`,
        isLoaded: () => workflowStore.isWorkflowListLoaded(variant),
        fetchListing: () => workflowStore.fetchWorkflowList(variant, "", { limit: PALETTE_LIMITS.page }),
        cachedItems: () => workflowRows(workflowStore.getWorkflowList(variant), variant),
        isComplete: () => workflowStore.getWorkflowList(variant).length < PALETTE_LIMITS.page,
        searchItems:
            variant === "bookmarked"
                ? undefined
                : async (query) => {
                      await workflowStore.fetchWorkflowList(variant, query, { limit: PALETTE_LIMITS.page });
                      return workflowStore
                          .getWorkflowList(variant, query)
                          .map((workflow) => workflowItem(workflow, variant));
                  },
    };
}

/** The root answer's search of one list, answering with this query's rows alone */
function listingSearch(variant: WorkflowListVariant): ListingSearch {
    return async (query) => {
        const found = await useWorkflowStore().fetchWorkflowList(variant, query, { limit: PALETTE_LIMITS.page });
        return found.map((workflow) => workflowItem(workflow, variant));
    };
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
    return storeFirstItems(workflowList("my"), query.trim(), limit);
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
    /** Root mode: the cached own workflows, and the shared and published lists searched */
    search(query: string, ctx: PaletteContext, options: PaletteSearchOptions = {}) {
        // an anonymous visitor has neither own nor shared-with-me workflows
        const listings: WorkflowListVariant[] = ctx.isAnonymous ? ["published"] : ["shared", "published"];
        const own = ctx.isAnonymous ? undefined : workflowList("my");
        return rootListItems(query, own, listings.map(listingSearch), options);
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
            variant === "my" ? storeFirstItems(workflowList("bookmarked"), query, PALETTE_LIMITS.recent) : [],
            storeFirstItems(workflowList(variant), query, PALETTE_LIMITS.section),
        ]);
        return [
            ...section("bookmarked", "Bookmarked", bookmarked),
            ...section("recent", "Recent", variant === "my" ? recentItems(query) : []),
            ...section(variant, resultsTitle(scope, query), results),
        ];
    },
};
