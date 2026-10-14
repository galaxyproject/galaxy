/** Row caps and query thresholds shared by the palette providers, so sections of a kind size alike */
export const PALETTE_LIMITS = {
    /** Rows of any result section: scoped, root, category, recent, bookmarked and action argument rows */
    section: 8,
    /** Own, cached rows in a root answer */
    rootOwn: 5,
    /** Rows each listing searched on the backend contributes to a root answer, before the section cap */
    rootListing: 3,
    /** Entries per listing fetch; a page that comes back shorter is the whole listing */
    page: 25,
    /** Shortest query sent to a backend search; the cache answers anything shorter */
    minBackendQuery: 2,
    /** Tools keep the tool panel's three characters: the cached toolbox matches shorter queries */
    minToolBackendQuery: 3,
    /** Pause in ms, on top of the input debounce, before a root search reaches the backend */
    backendSettle: 250,
} as const;
