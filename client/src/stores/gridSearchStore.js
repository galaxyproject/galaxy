/**
 * Vuex store module used for managing search parameters in the grid. Currently
 * only manages the tags that access this store via the new tagging components,
 * but presumably the entire grid search filter criteria will live here one day.
 */
import { defineStore } from "pinia";

export const useGridSearchStore = defineStore("gridSearchStore", {
    state: () => ({
        searchTags: new Set(),
    }),
    actions: {
        async toggleSearchTag(text) {
            try {
                const tags = this.searchTags;
                tags.has(text) ? tags.delete(text) : tags.add(text);
            } catch (err) {
                console.log("Error: in toggleSearchTag", err);
            }
        },
        async removeSearchTag(text) {
            try {
                const tags = this.searchTags;
                tags.delete(text);
            } catch (err) {
                console.log("Error: in removeSearchTag", err);
            }
        },
        async clearSearchTags() {
            try {
                this.searchTags = new Set();
            } catch (err) {
                console.log("Error: in clearSearchTag", err);
            }
        },
    },
});
