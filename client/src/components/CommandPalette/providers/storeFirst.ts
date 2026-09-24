/** Store-first search of the listing providers: the cache answers each keystroke, the backend only what it cannot */
import type { PaletteItem, PaletteSearchOptions } from "../types";
import { dedupePaletteItemsByEntity, rankPaletteItems } from "../utilities";
import { PaletteFetchError } from "./errors";
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
    /** Backend search for `query`; rows the store merges into the listing come back through the cache */
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
 * Fetches the listing once, then refreshes it in the background once stale (see {@link refreshListWhenStale}).
 * Stores share identical in-flight fetches, but own histories resolve early while another load runs.
 */
export async function ensureListHydrated(list: StoreFirstList): Promise<void> {
    if (list.isLoaded()) {
        refreshListWhenStale(list.key, () => list.fetchListing());
        return;
    }
    try {
        await list.fetchListing();
    } catch (error) {
        // only a cache with nothing to fall back on reports the failure
        if (list.cachedItems().length === 0) {
            throw new PaletteFetchError(error);
        }
        console.debug("Command palette could not fetch a list", list.key, error);
    }
    markListRefreshed(list.key);
}

/**
 * Rows of `list` matching `query`; the backend is asked only for a long enough query the incomplete cache cannot
 * fill, and its loose matches are ranked locally too. `cacheOnly` never requests, not even to hydrate.
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
 * Root answer of a listing provider: the own list from cache, other listings searched on the backend (a whole
 * page each, as their newest rows often rank away). Copies collapse into the own row; failures add nothing.
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
