/**
 * The store-first search shared by the providers that list entities (histories,
 * workflows, reports, visualizations): the cached list renders at once and
 * answers every keystroke, and the backend is only asked for what it cannot.
 */
import type { PaletteItem, PaletteSearchOptions } from "../types";
import { dedupePaletteItemsByEntity, rankPaletteItems } from "../utilities";
import { fetchOrFail } from "./errors";
import { PALETTE_LIMITS } from "./limits";
import { markListRefreshed, refreshListWhenStale } from "./refresh";

/** One store-backed list, as the store-first search reads and fills it */
export interface StoreFirstList {
    /** Identity in the refresh bookkeeping, by convention `provider:variant` */
    key: string;
    /** Whether the store holds the unfiltered listing yet */
    isLoaded(): boolean;
    /** Fetches the unfiltered listing into the store, hydrating or refreshing it */
    fetchListing(): Promise<unknown>;
    /** The cached listing as rows, in the order an empty query shows them */
    cachedItems(): PaletteItem[];
    /** Whether the cache is everything the backend has, so it answers any query alone */
    isComplete(): boolean;
    /**
     * Asks the backend for `query`, resolving the rows it found. Rows the store
     * merges into the listing are read back from the cache as well. Unset for a
     * list the backend cannot narrow down further.
     */
    searchItems?(query: string): Promise<PaletteItem[]>;
}

/** A backend search of one more listing the root answer covers, resolving its matches */
export type ListingSearch = (query: string) => Promise<PaletteItem[]>;

/** A failing search degrades to whatever the cache already answered with */
async function searchQuietly(search: () => Promise<PaletteItem[]>): Promise<PaletteItem[]> {
    try {
        return await search();
    } catch (error) {
        console.debug("Command palette could not search a list", error);
        return [];
    }
}

/**
 * Fills an empty cache once — a failure is reported then, there being nothing to
 * fall back on — and afterwards only refreshes it in the background once stale
 * (see {@link refreshListWhenStale}). The stores share a request already running,
 * so a keystroke landing during the very first fetch waits for it instead of
 * rendering the still empty cache as "no results".
 */
export async function ensureListHydrated(list: StoreFirstList): Promise<void> {
    if (!list.isLoaded()) {
        await fetchOrFail(() => list.fetchListing());
        markListRefreshed(list.key);
    } else {
        refreshListWhenStale(list.key, () => list.fetchListing());
    }
}

/**
 * Rows of `list` matching `query`, store first: the backend is only asked when the
 * query is long enough, the cache is incomplete and it cannot fill `limit` rows.
 * The found rows are merged with the cache, one row per entity, and ranked the
 * same way — the backends match loosely, so their rows are ranked locally too.
 *
 * @param options.cacheOnly never request anything, not even to hydrate an empty
 * cache; the root answer passes it for the user's own list
 */
export async function storeFirstItems(
    list: StoreFirstList,
    query: string,
    limit: number,
    options: { cacheOnly?: boolean } = {},
): Promise<PaletteItem[]> {
    if (!options.cacheOnly) {
        await ensureListHydrated(list);
    }
    const local = rankPaletteItems(list.cachedItems(), query);
    const search = list.searchItems;
    if (
        options.cacheOnly ||
        !search ||
        query.length < PALETTE_LIMITS.minBackendQuery ||
        list.isComplete() ||
        local.length >= limit
    ) {
        return local.slice(0, limit);
    }
    const found = await searchQuietly(() => search(query));
    const merged = dedupePaletteItemsByEntity([...rankPaletteItems(list.cachedItems(), query), ...found]);
    return rankPaletteItems(merged, query).slice(0, limit);
}

/**
 * Root mode answer of a listing provider: the user's own list answers from the
 * cache, while the other listings are searched on the backend — the palette is
 * the one place that finds an entity without being told where it lives. Copies
 * of one entity collapse into the own row, which knows what the user may do with
 * it, and a failing listing contributes nothing. The palette's debounce keeps
 * the request volume down.
 *
 * @param own the user's own list, unset for an anonymous visitor
 * @param listings backend searches of the other listings; each one fetches a
 * whole page although only a few rows are shown, since the backend orders by
 * update time and its newest rows are often ranked away here
 */
export async function rootListItems(
    query: string,
    own: StoreFirstList | undefined,
    listings: ListingSearch[],
    options: PaletteSearchOptions = {},
): Promise<PaletteItem[]> {
    if (query.length < PALETTE_LIMITS.minBackendQuery) {
        return [];
    }
    // the searches start before the cache is filtered, so they run in parallel
    const listed = Promise.all(
        (options.localOnly ? [] : listings).map(async (search) =>
            rankPaletteItems(await searchQuietly(() => search(query)), query).slice(0, PALETTE_LIMITS.rootListing),
        ),
    );
    const ownItems = own ? await storeFirstItems(own, query, PALETTE_LIMITS.rootOwn, { cacheOnly: true }) : [];
    const merged = dedupePaletteItemsByEntity([ownItems, ...(await listed)].flat());
    return rankPaletteItems(merged, query).slice(0, PALETTE_LIMITS.rootOwn + PALETTE_LIMITS.rootListing);
}
