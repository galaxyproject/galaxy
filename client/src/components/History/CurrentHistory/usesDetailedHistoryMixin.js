/**
 * VueJS mixin exposing extended properties for a history in a safe way.
 * If the values haven't been loaded yet the computed properties will return 0 instead of undefined.
 */
export const usesDetailedHistoryMixin = {
    computed: {
        /** The total size in bytes of the sum of all the items in this history. */
        historySize() {
            return this.history.size || 0;
        },
        /** The number of items currently active (usable). */
        numItemsActive() {
            return this.history.contents_active?.active || 0;
        },
        /** The number of items deleted and/or purged. */
        numItemsDeleted() {
            return this.history.contents_active?.deleted || 0;
        },
        /** The number of items hidden. */
        numItemsHidden() {
            return this.history.contents_active?.hidden || 0;
        },
    },
};
