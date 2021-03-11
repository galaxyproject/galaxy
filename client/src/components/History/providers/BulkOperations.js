import { SearchParams } from "../model";

const operations = [
    { text: "Hide", value: "hide" },
    { text: "Unhide", value: "unhide" },
    { text: "Delete", value: "delete" },
    { text: "Undelete", value: "undelete" },
    { text: "Permanently Delete", value: "purge" },
    { text: "Undelete", value: "undelete" },
    { text: "Build Dataset List", value: "buildDatasetList" },
    { text: "Build Dataset Pair", value: "buildDatasetPair" },
    { text: "Build List of Dataset Pairs", value: "buildListOfPairs" },
    { text: "Build Collection from Rules", value: "buildCollectionFromRules" },
];

/**
 * Executes bulk operations against a selection. A selection can be either an individual list of
 * items or a query-based representation that will select against the entire history
 */
export default {
    props: {
        /**
         * History on which we are operating
         */
        history: { type: Object, required: true },

        /**
         * Search parameters used in query-based selection
         */
        filters: { type: SearchParams, required: false, default: () => new SearchParams() },

        /**
         * A set of type_ids used in bulk operations against this history
         */
        contentSelection: { type: Set, required: false, default: () => new Set() },

        /**
         * Toggles individual item selection or query-based selection
         */
        itemMode: { type: Boolean, required: false, default: false },
    },
    computed: {
        operations() {
            // TODO: should filter out available options based on selection
            return operations;
        },
        slotProps() {
            return { operations: this.operations, execute: this.execute };
        },
    },
    methods: {
        execute(...args) {
            console.log("executing", ...args);
        },
    },
    render() {
        return this.$scopedSlots.default(this.slotProps);
    },
};
