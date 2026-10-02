/**
 * Stale-while-revalidate for the store backed palette lists.
 *
 * Every scoped provider (workflows, histories, pages, visualizations, datasets,
 * invocations) hydrates its store once and then answers keystrokes from that
 * cache. Without this helper the cache would stay as old as the first palette
 * use for the rest of the session -- a workflow renamed in another tab would
 * keep its old title until a reload.
 *
 * The guard is a wall clock timestamp per list rather than an "epoch" handed
 * down from the palette component: it needs no plumbing through the palette
 * context, and reopening the palette a moment later still renders instantly
 * from the cache instead of re-requesting every list.
 *
 * A refresh is deliberately *not* awaited. The cached rows are what the user
 * sees now; the fresh ones land in the store and show up on the next keystroke.
 */

/** How long a hydrated list is served without asking the backend again. */
export const LIST_REFRESH_INTERVAL_MS = 60_000;

/** When each list was last hydrated or refreshed, keyed by `provider:variant`. */
const refreshedAt = new Map<string, number>();

/** Records that `key` has just been fetched, so no refresh is due yet. */
export function markListRefreshed(key: string): void {
    refreshedAt.set(key, Date.now());
}

/**
 * Refreshes `key` in the background when its cache has not been fetched within
 * {@link LIST_REFRESH_INTERVAL_MS}. Returns immediately either way; a failing
 * refresh is swallowed, leaving the cached list in place.
 *
 * @param key list identity, by convention `provider:variant`
 * @param refresh fetches the unfiltered list into its store
 */
export function refreshListWhenStale(key: string, refresh: () => Promise<unknown>): void {
    const previous = refreshedAt.get(key);
    if (previous !== undefined && Date.now() - previous < LIST_REFRESH_INTERVAL_MS) {
        return;
    }
    markListRefreshed(key);
    void (async () => {
        try {
            await refresh();
        } catch (error) {
            console.debug("Command palette could not refresh a cached list", key, error);
        }
    })();
}

/** Test seam: forgets every recorded refresh. */
export function resetListRefreshTracking(): void {
    refreshedAt.clear();
}
