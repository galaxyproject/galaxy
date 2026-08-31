/**
 * Caches page summaries for list-like consumers (command palette scopes, pickers).
 *
 * The store is the single source of truth: fetches merge their results into the
 * `summariesById` cache and only keep id lists per variant, so no page is duplicated.
 */
import { defineStore } from "pinia";
import { computed, del, ref, set } from "vue";

import { loadPages, type LoadPagesOptions, type PageSummary } from "@/api/pages";

/** `my` = pages owned by the current user, `published` = published (and shared) pages. */
export type PageListVariant = "my" | "published";

const VARIANT_QUERY: Record<PageListVariant, Pick<LoadPagesOptions, "showOwn" | "showShared" | "showPublished">> = {
    my: { showOwn: true, showShared: false, showPublished: false },
    published: { showOwn: false, showShared: true, showPublished: true },
};

export type FetchPagesOptions = Omit<LoadPagesOptions, "showOwn" | "showShared" | "showPublished">;

export const usePageStore = defineStore("pageStore", () => {
    const summariesById = ref<Record<string, PageSummary>>({});
    const idsByVariant = ref<Record<PageListVariant, string[]>>({ my: [], published: [] });
    const totalMatchesByVariant = ref<Record<PageListVariant, number>>({ my: 0, published: 0 });
    const loadedVariants = ref<Record<PageListVariant, boolean>>({ my: false, published: false });
    const loadingVariants = ref<Record<PageListVariant, boolean>>({ my: false, published: false });

    /** In-flight requests, keyed by variant and query, to avoid duplicate fetches. */
    const fetchPromises = new Map<string, Promise<PageSummary[]>>();

    const getPageById = computed(() => (pageId: string) => summariesById.value[pageId]);

    const getPages = computed(() => (variant: PageListVariant) => {
        const pages: PageSummary[] = [];
        for (const pageId of idsByVariant.value[variant]) {
            const page = summariesById.value[pageId];
            if (page) {
                pages.push(page);
            }
        }
        return pages;
    });

    const myPages = computed(() => getPages.value("my"));
    const publishedPages = computed(() => getPages.value("published"));

    const isLoaded = computed(() => (variant: PageListVariant) => loadedVariants.value[variant]);
    const isLoading = computed(() => (variant: PageListVariant) => loadingVariants.value[variant]);

    /** True when the cached id list is known to hold every page of that variant. */
    const isComplete = computed(
        () => (variant: PageListVariant) =>
            loadedVariants.value[variant] && idsByVariant.value[variant].length >= totalMatchesByVariant.value[variant],
    );

    function mergeIds(existing: string[], incoming: string[], atFront: boolean) {
        if (atFront) {
            const incomingIds = new Set(incoming);
            return [...incoming, ...existing.filter((pageId) => !incomingIds.has(pageId))];
        }
        const existingIds = new Set(existing);
        return [...existing, ...incoming.filter((pageId) => !existingIds.has(pageId))];
    }

    /** Merges pages into the summary cache and into the given variant's id list. */
    function savePages(variant: PageListVariant, pages: PageSummary[], atFront = false) {
        const incomingIds: string[] = [];
        for (const page of pages) {
            set(summariesById.value, page.id, page);
            incomingIds.push(page.id);
        }
        set(idsByVariant.value, variant, mergeIds(idsByVariant.value[variant], incomingIds, atFront));
    }

    /** Removes a page from the cache and from every variant list. */
    function removePage(pageId: string) {
        del(summariesById.value, pageId);
        for (const variant of Object.keys(idsByVariant.value) as PageListVariant[]) {
            set(
                idsByVariant.value,
                variant,
                idsByVariant.value[variant].filter((id) => id !== pageId),
            );
        }
    }

    /**
     * Fetches pages of the given variant from the server and merges them into the cache.
     * Concurrent identical requests share a single promise.
     */
    async function fetchPages(variant: PageListVariant, options: FetchPagesOptions = {}): Promise<PageSummary[]> {
        const { search = "", sortBy = "update_time", sortDesc = true, limit = 20, offset = 0 } = options;
        const key = [variant, search, sortBy, sortDesc, limit, offset].join("|");

        const pending = fetchPromises.get(key);
        if (pending) {
            return pending;
        }

        const isFullListing = !search && offset === 0;

        const promise = (async () => {
            set(loadingVariants.value, variant, true);
            try {
                const { data, totalMatches } = await loadPages({
                    ...VARIANT_QUERY[variant],
                    search,
                    sortBy,
                    sortDesc,
                    limit,
                    offset,
                });
                savePages(variant, data, isFullListing);
                if (isFullListing) {
                    set(totalMatchesByVariant.value, variant, totalMatches);
                }
                set(loadedVariants.value, variant, true);
                return data;
            } finally {
                set(loadingVariants.value, variant, false);
                fetchPromises.delete(key);
            }
        })();

        fetchPromises.set(key, promise);

        return promise;
    }

    /** Fetches the variant once; later calls resolve from the cache. */
    async function fetchPagesOnce(variant: PageListVariant, options: FetchPagesOptions = {}): Promise<PageSummary[]> {
        if (loadedVariants.value[variant]) {
            return getPages.value(variant);
        }
        await fetchPages(variant, options);
        return getPages.value(variant);
    }

    return {
        // state
        summariesById,
        idsByVariant,
        totalMatchesByVariant,
        // getters
        getPageById,
        getPages,
        myPages,
        publishedPages,
        isLoaded,
        isLoading,
        isComplete,
        // actions
        savePages,
        removePage,
        fetchPages,
        fetchPagesOnce,
    };
});
