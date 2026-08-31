import { faHdd } from "@fortawesome/free-solid-svg-icons";
import { formatDistanceToNow } from "date-fns";

import { HistoriesFilters } from "@/components/History/HistoriesFilters";
import { useRecentPaletteItems } from "@/composables/useRecentPaletteItems";
import { type HistoryListVariant, useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import { galaxyTimeToDate } from "@/utils/dates";

import type { CommandPaletteProvider, PaletteContext, PaletteItem, ScopedSection } from "../types";
import { rankPaletteItems } from "../utilities";
import type { ScopeDefinition } from "./scopes";

/** Entity type this provider records in the palette MRU (`useRecentPaletteItems`) */
export const HISTORY_RECENT_TYPE = "history";

/** Per section caps, kept small so both sections fit without scrolling */
const RESULTS_LIMIT = 8;
const RECENT_LIMIT = 5;
const ROOT_LIMIT = 5;

/** Neither the unscoped fan-out nor a backend query runs on a single character */
const MIN_QUERY_LENGTH = 2;

/** Entries requested per fetch of one of the cached (foreign) listings */
const LIST_PAGE_SIZE = 25;

/** Which cached list a scope reads: the user's own histories, or a listing */
type HistoryVariant = "my" | HistoryListVariant;

/**
 * The fields this provider reads off a history. The store keeps the user's own
 * histories (`AnyHistory`, serialized without `username`) apart from the shared,
 * published and archived listings (`AnyHistoryEntry`, which carry the owner), so
 * the two sources are narrowed to their common, optional shape here.
 */
interface HistoryEntryLike {
    id: string;
    name: string;
    annotation?: string | null;
    count?: number;
    owner?: string;
    tags?: string[];
    update_time?: string;
    username?: string;
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
 * `h:` and `ha:` list the user's own histories by definition. The shared and
 * published listings may mix owners, and are requested with the `username` key
 * so the owner is known. Own histories are serialized without `username`, but
 * the store deliberately keeps foreign listings out of `storedHistories`, so
 * being cached there identifies a history as the user's own.
 */
function ownsHistory(history: HistoryEntryLike, variant: HistoryVariant): boolean {
    if (variant === "archived") {
        return true;
    }
    if (history.username) {
        return useUserStore().matchesCurrentUsername(history.username);
    }
    return Boolean(useHistoryStore().storedHistories[history.id]);
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

/** The annotation says more than a bare item count, so it wins when present */
function describeContents(history: HistoryEntryLike): string | undefined {
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
function historyItem(history: HistoryEntryLike, sectionId: string, variant: HistoryVariant): PaletteItem {
    const historyStore = useHistoryStore();
    const isCurrent = historyStore.currentHistoryId === history.id;
    const owned = ownsHistory(history, variant);
    const subtitle = [
        isCurrent ? "(current)" : undefined,
        describeContents(history),
        // the owner is only worth a line for histories that are not the user's own
        owned ? undefined : (history.owner ?? history.username) && `by ${history.owner ?? history.username}`,
        updatedLabel(history.update_time),
    ]
        .filter(Boolean)
        .join(" · ");
    return {
        id: itemId(sectionId, history.id),
        icon: faHdd,
        keywords: [history.owner, history.username, ...(history.tags ?? [])].filter(Boolean).join(" "),
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

/** Newest first, so an empty query renders the "Latest" section as promised */
function latestFirst(histories: HistoryEntryLike[]): HistoryEntryLike[] {
    return [...histories].sort((a, b) => (b.update_time ?? "").localeCompare(a.update_time ?? ""));
}

/** A failing background fetch degrades to whatever the store already holds */
async function fetchQuietly(fetch: () => Promise<unknown>) {
    try {
        await fetch();
    } catch (error) {
        console.debug("Command palette could not fetch histories", error);
    }
}

/** The cached histories of one variant, straight from the store */
function cachedHistories(variant: HistoryVariant): HistoryEntryLike[] {
    const historyStore = useHistoryStore();
    if (variant === "my") {
        return historyStore.histories as unknown as HistoryEntryLike[];
    }
    return historyStore.getListedHistories(variant) as unknown as HistoryEntryLike[];
}

/** Fills an empty cache once; a populated cache answers the keystroke as is */
async function ensureHydrated(variant: HistoryVariant): Promise<void> {
    const historyStore = useHistoryStore();
    if (variant === "my") {
        if (historyStore.histories.length === 0 && !historyStore.historiesLoading) {
            // unpaginated: the whole own list, so later keystrokes stay local
            await fetchQuietly(() => historyStore.loadHistories(false));
        }
        return;
    }
    if (!historyStore.hasLoadedHistoryList(variant)) {
        await fetchQuietly(() => historyStore.ensureHistoryListLoaded(variant, { limit: LIST_PAGE_SIZE }));
    }
}

/** Asks the backend for `query` through the store, which merges the result in */
async function searchBackend(variant: HistoryVariant, query: string): Promise<void> {
    const historyStore = useHistoryStore();
    if (variant === "my") {
        await fetchQuietly(() => historyStore.loadHistories(false, HistoriesFilters.getQueryString(query)));
        return;
    }
    await fetchQuietly(() => historyStore.fetchHistoryList(variant, { search: query, limit: LIST_PAGE_SIZE }));
}

function rankHistories(histories: HistoryEntryLike[], variant: HistoryVariant, query: string): PaletteItem[] {
    return rankPaletteItems(
        latestFirst(histories).map((history) => historyItem(history, variant, variant)),
        query,
    );
}

/**
 * Whether the cache holds everything the backend has, in which case it can
 * answer any query on its own.
 *
 * The listings are fetched a page at a time, so a short page is the whole list.
 * The own histories are fetched unpaginated instead, which leaves the total
 * unknown (zero) — it is only set when the app itself paginated the list, and
 * then it says how much of it is still missing.
 */
function cacheIsComplete(variant: HistoryVariant, cached: HistoryEntryLike[]): boolean {
    if (variant === "my") {
        return cached.length >= useHistoryStore().totalHistoryCount;
    }
    return cached.length < LIST_PAGE_SIZE;
}

/**
 * Store first section data: the cached list renders instantly and answers every
 * keystroke locally. The backend is only asked when the cache is empty, or when
 * an incomplete cache cannot fill the section for the current query — its result
 * is merged into the store (deduplicated by id there) and read back from the
 * same cache.
 *
 * @param variant which cached list to read
 * @param query free text filter, already trimmed
 * @param limit section cap
 * @param cacheOnly never request anything, not even to hydrate an empty cache —
 * the unscoped root fan-out runs on every provider at once and only filters
 * what the stores already hold; the scopes do the fetching.
 */
async function listItems(
    variant: HistoryVariant,
    query: string,
    limit: number,
    cacheOnly = false,
): Promise<PaletteItem[]> {
    if (!cacheOnly) {
        await ensureHydrated(variant);
    }
    const cached = cachedHistories(variant);
    const local = rankHistories(cached, variant, query);
    if (cacheOnly || query.length < MIN_QUERY_LENGTH || cacheIsComplete(variant, cached) || local.length >= limit) {
        return local.slice(0, limit);
    }
    await searchBackend(variant, query);
    return rankHistories(cachedHistories(variant), variant, query).slice(0, limit);
}

/** Histories opened through the palette before, most recently used first */
function recentItems(query: string, limit = RECENT_LIMIT): PaletteItem[] {
    const historyStore = useHistoryStore();
    const { recentItems: recentEntries } = useRecentPaletteItems();
    const items = recentEntries(HISTORY_RECENT_TYPE).map((entry) => {
        const summary = (historyStore.storedHistories[entry.id] ?? historyStore.listedHistories[entry.id]) as
            | HistoryEntryLike
            | undefined;
        return summary
            ? historyItem(summary, "recent", "my")
            : {
                  id: itemId("recent", entry.id),
                  icon: faHdd,
                  mru: { type: HISTORY_RECENT_TYPE, id: entry.id },
                  title: entry.name,
                  to: entry.to ?? viewUrl(entry.id),
              };
    });
    return rankPaletteItems(items, query).slice(0, limit);
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
        return recentItems("", ROOT_LIMIT);
    },
    /** Root mode fan-out, filtering the cached own histories without a request */
    async search(query: string, ctx: PaletteContext) {
        const trimmed = query.trim();
        if (ctx.isAnonymous || trimmed.length < MIN_QUERY_LENGTH) {
            return [];
        }
        return listItems("my", trimmed, ROOT_LIMIT, true);
    },
    /**
     * `h:`, `hs:`, `hp:` and `ha:` all show the palette recents on top of the
     * matching listing. The query filters both sections; an empty query leaves
     * the listing showing the most recently updated histories.
     */
    async searchScoped(scope: ScopeDefinition, query: string) {
        const variant = listVariant(scope.variant);
        const trimmed = query.trim();
        const results = await listItems(variant, trimmed, RESULTS_LIMIT);
        return [
            ...section("recent", "Recent", recentItems(trimmed)),
            ...section(variant, resultsTitle(scope, trimmed), results),
        ];
    },
};
