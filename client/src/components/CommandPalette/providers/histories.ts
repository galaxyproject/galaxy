import { faHdd } from "@fortawesome/free-solid-svg-icons";

import type { AnyHistory } from "@/api";
import type { AnyHistoryEntry } from "@/api/histories";
import { HistoriesFilters } from "@/components/History/HistoriesFilters";
import { type HistoryListVariant, useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import { relativeUpdatedLabel } from "@/utils/dates";

import type {
    CommandPaletteProvider,
    PaletteContext,
    PaletteItem,
    PaletteSearchOptions,
    ScopedSection,
} from "../types";
import { PALETTE_LIMITS } from "./limits";
import { recentPaletteItems, type RecentRows } from "./recent";
import type { ScopeDefinition } from "./scopes";
import { type ListingSearch, rootListItems, storeFirstItems, type StoreFirstList } from "./storeFirst";

/** Entity type this provider records in the palette MRU (`useRecentPaletteItems`) */
export const HISTORY_RECENT_TYPE = "history";

/** Which cached list a scope reads: the user's own histories, or a listing */
type HistoryVariant = "my" | HistoryListVariant;

/** The fields a palette row reads off a history, whichever store list it came from */
interface PaletteHistory {
    id: string;
    name: string;
    annotation: string | null;
    count: number;
    /** The owner's username; unset for own histories, which are serialized without one */
    owner?: string;
    tags: string[];
    update_time: string;
}

/** Own and listed histories as one shape; the backend sends the owner as `username`, listings alone add `owner` */
function toPaletteHistory(history: AnyHistory | AnyHistoryEntry): PaletteHistory {
    const owner = ("username" in history && history.username) || ("owner" in history && history.owner) || undefined;
    return {
        id: history.id,
        name: history.name,
        annotation: history.annotation,
        count: history.count,
        owner,
        tags: history.tags,
        update_time: history.update_time,
    };
}

/** Scope variant (`undefined` | `shared` | `published` | `archived`) to list */
function listVariant(variant?: string): HistoryVariant {
    switch (variant) {
        case "shared":
            return "shared";
        case "published":
            return "published";
        case "archived":
            return "archived";
        default:
            return "my";
    }
}

function viewUrl(historyId: string): string {
    return `/histories/view?id=${historyId}`;
}

/** Section scoped item id, so the same history may appear in several sections */
function itemId(sectionId: string, historyId: string): string {
    return `histories:${sectionId}:${historyId}`;
}

/**
 * Whether the current user may make this history their current one.
 *
 * The owner decides it: the shared and published listings may mix owners and
 * are requested with the `username` key, so whenever an owner is known it is
 * matched against the current user. Being cached in `storedHistories` is not
 * proof of ownership -- any history opened by id lands there, including foreign
 * published ones. Only the listings that are the user's own by definition (`h:`
 * and `ha:`, both served by endpoints that never return another user's history)
 * count an entry without an owner as owned.
 */
function ownsHistory(history: PaletteHistory, variant: HistoryVariant): boolean {
    if (history.owner) {
        return useUserStore().matchesCurrentUsername(history.owner);
    }
    return variant === "my" || variant === "archived";
}

/** The annotation says more than a bare item count, so it wins when present */
function describeContents(history: PaletteHistory): string | undefined {
    const annotation = history.annotation?.trim();
    if (annotation) {
        return annotation;
    }
    if (typeof history.count !== "number") {
        return undefined;
    }
    return history.count === 1 ? "1 item" : `${history.count} items`;
}

/**
 * One result row. Enter opens the history in the history view; histories the
 * current user owns additionally switch to it on shift+enter.
 */
function historyItem(history: PaletteHistory, sectionId: string, variant: HistoryVariant): PaletteItem {
    const historyStore = useHistoryStore();
    const isCurrent = historyStore.currentHistoryId === history.id;
    const owned = ownsHistory(history, variant);
    const subtitle = [
        isCurrent ? "(current)" : undefined,
        describeContents(history),
        // the owner is only worth a line for histories that are not the user's own
        owned ? undefined : history.owner && `by ${history.owner}`,
        relativeUpdatedLabel(history.update_time),
    ]
        .filter(Boolean)
        .join(" · ");
    return {
        id: itemId(sectionId, history.id),
        icon: faHdd,
        keywords: [history.owner, ...history.tags].filter(Boolean).join(" "),
        mru: { type: HISTORY_RECENT_TYPE, id: history.id },
        title: history.name,
        to: viewUrl(history.id),
        ...(subtitle ? { subtitle } : {}),
        ...(owned && !isCurrent
            ? {
                  secondaryAction: {
                      label: "Set as current",
                      run: () => {
                          void historyStore.setCurrentHistory(history.id);
                      },
                  },
              }
            : {}),
    };
}

/** Rows of one list, newest first so an empty query renders "Latest" as promised */
function historyRows(histories: PaletteHistory[], variant: HistoryVariant): PaletteItem[] {
    return [...histories]
        .sort((a, b) => b.update_time.localeCompare(a.update_time))
        .map((history) => historyItem(history, variant, variant));
}

/** The cached histories of one variant, straight from the store */
function cachedHistories(variant: HistoryVariant): PaletteHistory[] {
    const historyStore = useHistoryStore();
    const histories = variant === "my" ? historyStore.histories : historyStore.getListedHistories(variant);
    return histories.map(toPaletteHistory);
}

/** One history list, store first; every variant fetches a single page, as the palette shows a handful of rows */
function historyList(variant: HistoryVariant): StoreFirstList {
    const historyStore = useHistoryStore();
    return {
        key: `histories:${variant}`,
        isLoaded: () =>
            variant === "my" ? historyStore.histories.length > 0 : historyStore.hasLoadedHistoryList(variant),
        fetchListing: () =>
            variant === "my"
                ? historyStore.loadHistories(false, undefined, PALETTE_LIMITS.page)
                : historyStore.fetchHistoryList(variant, { limit: PALETTE_LIMITS.page }),
        cachedItems: () => historyRows(cachedHistories(variant), variant),
        // a short page is the whole list; the own histories additionally carry a
        // total whenever the app paginated them itself, and it stays zero otherwise
        isComplete: () => {
            const cached = cachedHistories(variant).length;
            const total = variant === "my" ? historyStore.totalHistoryCount : 0;
            return cached < PALETTE_LIMITS.page && cached >= total;
        },
        async searchItems(query) {
            if (variant === "my") {
                // merged into the own histories, which the cache read picks up
                await historyStore.loadHistories(false, HistoriesFilters.getQueryString(query), PALETTE_LIMITS.page);
                return [];
            }
            const found = await historyStore.fetchHistoryList(variant, { search: query, limit: PALETTE_LIMITS.page });
            return historyRows(found.map(toPaletteHistory), variant);
        },
    };
}

/** Root-answer search of one listing; `record: false` keeps the matches out of the listing `hs:`/`hp:` hydrate */
function listingSearch(variant: HistoryListVariant): ListingSearch {
    return async (query) => {
        const found = await useHistoryStore().fetchHistoryList(variant, {
            search: query,
            limit: PALETTE_LIMITS.page,
            record: false,
        });
        return historyRows(found.map(toPaletteHistory), variant);
    };
}

/** Histories opened through the palette before, most recently used first */
function recentItems(query: string, limit = PALETTE_LIMITS.recent): PaletteItem[] {
    const historyStore = useHistoryStore();
    const rows: RecentRows = {
        type: HISTORY_RECENT_TYPE,
        stored: (entry) => {
            const summary = historyStore.storedHistories[entry.id] ?? historyStore.listedHistories[entry.id];
            return summary ? historyItem(toPaletteHistory(summary), "recent", "my") : undefined;
        },
        fallback: (entry) => ({ id: itemId("recent", entry.id), icon: faHdd, to: viewUrl(entry.id) }),
    };
    return recentPaletteItems(rows, query, limit);
}

function resultsTitle(scope: ScopeDefinition, query: string): string {
    if (!query) {
        return "Latest";
    }
    return scope.variant ? scope.label : "Histories";
}

function section(id: string, title: string, items: PaletteItem[]): ScopedSection[] {
    return items.length ? [{ id, items, title }] : [];
}

export const historiesProvider: CommandPaletteProvider = {
    id: "histories",
    title: "Histories",
    /** Root mode: histories the palette remembers, no request needed */
    emptyQueryItems(ctx: PaletteContext) {
        if (ctx.isAnonymous) {
            return [];
        }
        return recentItems("", PALETTE_LIMITS.rootOwn);
    },
    /** Root mode: the cached own histories, and the shared and published listings searched */
    search(query: string, ctx: PaletteContext, options: PaletteSearchOptions = {}) {
        // an anonymous visitor has neither own nor shared-with-me histories
        const listings: HistoryListVariant[] = ctx.isAnonymous ? ["published"] : ["shared", "published"];
        const own = ctx.isAnonymous ? undefined : historyList("my");
        return rootListItems(query, own, listings.map(listingSearch), options);
    },
    /**
     * `h:` shows the palette recents on top of the user's own listing; `hs:`,
     * `hp:` and `ha:` show their listing alone. The palette remembers one list
     * per entity type rather than per scope, so the recents belong to the base
     * scope only — the user's private (and unarchived) histories have no
     * business showing up under "shared", "public" or "archived". The query
     * filters both sections; an empty query leaves the listing showing the most
     * recently updated histories.
     */
    async searchScoped(scope: ScopeDefinition, query: string) {
        const variant = listVariant(scope.variant);
        const results = await storeFirstItems(historyList(variant), query, PALETTE_LIMITS.section);
        return [
            ...section("recent", "Recent", variant === "my" ? recentItems(query) : []),
            ...section(variant, resultsTitle(scope, query), results),
        ];
    },
};
