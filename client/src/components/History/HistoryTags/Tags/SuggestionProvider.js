/**
 * Match and process options for the autocomplete dropdown. Accepts a search query, a list of
 * currently selected tags, a list of available outocomplete options, emits a processed array of
 * objects { label, value } that match the query
 */

import { escape } from "validator";

const escapeRegExp = (str) => str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

export default {
    props: {
        query: { type: String, default: "" },
        selected: { type: Array, default: () => [] },
        available: { type: Array, default: () => [] },
    },

    data() {
        return {
            indexCounter: -1,
        };
    },

    computed: {
        cleanQuery() {
            return escapeRegExp(escape(this.query));
        },
        matchRegex() {
            return new RegExp(this.cleanQuery, "gi");
        },
        optionFilter() {
            const existingSet = new Set(this.selected);
            return (val) => !existingSet.has(val) && val.match(this.matchRegex);
        },
        options() {
            if (this.cleanQuery.length) {
                return this.available.filter(this.optionFilter).map(this.buildOption);
            }
            return [];
        },
        activeSuggestion() {
            return this.options.find((o) => o.active);
        },
    },

    methods: {
        // Adds a little markup to a label property, highlights text matches
        buildOption(value, i, allOptions) {
            const label = this.highlight(value);
            const active = this.indexCounter % allOptions.length == i;
            return { value, label, active };
        },
        highlight(val) {
            return val.replace(this.matchRegex, `<strong>$&</strong>`);
        },
        nextSuggestion() {
            this.indexCounter++;
        },
        lastSuggestion() {
            this.indexCounter--;
        },
        selectActive() {},
    },

    render() {
        return this.$scopedSlots.default({
            options: this.options,
            activeSuggestion: this.activeSuggestion,
            nextSuggestion: this.nextSuggestion,
            lastSuggestion: this.lastSuggestion,
        });
    },
};
