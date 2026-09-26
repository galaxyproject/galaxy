/** Row caps and query thresholds shared by the palette providers, so sections of a kind size alike */
export const PALETTE_LIMITS = {
    /** Rows of a scoped result section, and of an action's argument rows */
    section: 8,
    /** Rows of a "Recent" or "Bookmarked" section */
    recent: 5,
    /** Own, cached rows in a root answer */
    rootOwn: 5,
    /** Rows a root answer shows per listing it searched on the backend */
    rootListing: 3,
    /** Entries per listing fetch; a page that comes back shorter is the whole listing */
    page: 25,
    /** Shortest query sent to a backend search; the cache answers anything shorter */
    minBackendQuery: 2,
    /** Tools keep the tool panel's three characters: the cached toolbox matches shorter queries */
    minToolBackendQuery: 3,
} as const;
