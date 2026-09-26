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

export type FetchPagesOptions = Omit<LoadPagesOptions, "showOwn" | "showShared" | "showPublished"> & {
    /** Merge summaries by id without recording this request as the canonical variant listing. */
    record?: boolean;
};

export const usePageStore = defineStore("pageStore", () => {
    const summariesById = ref<Record<string, PageSummary>>({});
    const idsByVariant = ref<Record<PageListVariant, string[]>>({ my: [], published: [] });
    const totalMatchesByVariant = ref<Record<PageListVariant, number>>({ my: 0, published: 0 });
    const loadedVariants = ref<Record<PageListVariant, boolean>>({ my: false, published: false });
    const loadingVariants = ref<Record<PageListVariant, boolean>>({ my: false, published: false });
    /**
     * Whether an *unfiltered* listing of the variant has been fetched. Only such
     * a fetch reports how many pages exist in total, so only it can tell whether
     * the cached ids are the complete list.
     */
    const fullyListedVariants = ref<Record<PageListVariant, boolean>>({ my: false, published: false });

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

    /**
     * True when the cached id list is known to hold every page of that variant.
     * A search that came back empty proves nothing about the full list, so this
     * stays false until an unfiltered listing has reported the total.
     */
    const isComplete = computed(
        () => (variant: PageListVariant) =>
            fullyListedVariants.value[variant] &&
            idsByVariant.value[variant].length >= totalMatchesByVariant.value[variant],
    );

    function mergeIds(existing: string[], incoming: string[], atFront: boolean) {
        if (atFront) {
            const incomingIds = new Set(incoming);
            return [...incoming, ...existing.filter((pageId) => !incomingIds.has(pageId))];
        }
        const existingIds = new Set(existing);
        return [...existing, ...incoming.filter((pageId) => !existingIds.has(pageId))];
    }

    /** Merges pages into the shared summary cache without changing a variant listing. */
    function mergePageSummaries(pages: PageSummary[]) {
        for (const page of pages) {
            set(summariesById.value, page.id, page);
        }
    }

    /** Merges pages into the summary cache and into the given variant's id list. */
    function savePages(variant: PageListVariant, pages: PageSummary[], atFront = false) {
        mergePageSummaries(pages);
        const incomingIds = pages.map((page) => page.id);
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
        const { search = "", sortBy = "update_time", sortDesc = true, limit = 20, offset = 0, record = true } = options;
        const key = [variant, search, sortBy, sortDesc, limit, offset, record].join("|");

        const pending = fetchPromises.get(key);
        if (pending) {
            return pending;
        }

        const isFullListing = record && !search && offset === 0;

        const promise = (async () => {
            if (record) {
                set(loadingVariants.value, variant, true);
            }
            try {
                const { data, totalMatches } = await loadPages({
                    ...VARIANT_QUERY[variant],
                    search,
                    sortBy,
                    sortDesc,
                    limit,
                    offset,
                });
                if (record) {
                    savePages(variant, data, isFullListing);
                    if (isFullListing) {
                        set(totalMatchesByVariant.value, variant, totalMatches);
                        set(fullyListedVariants.value, variant, true);
                    }
                    set(loadedVariants.value, variant, true);
                } else {
                    mergePageSummaries(data);
                }
                return data;
            } finally {
                if (record) {
                    set(loadingVariants.value, variant, false);
                }
                fetchPromises.delete(key);
            }
        })();

        fetchPromises.set(key, promise);

        return promise;
    }

    /**
     * Fetches the variant once; later calls resolve from the cache.
     *
     * Always records, so that the variant it reads back is the one it hydrated.
     */
    async function fetchPagesOnce(
        variant: PageListVariant,
        options: Omit<FetchPagesOptions, "record"> = {},
    ): Promise<PageSummary[]> {
        if (loadedVariants.value[variant]) {
            return getPages.value(variant);
        }
        await fetchPages(variant, { ...options, record: true });
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
