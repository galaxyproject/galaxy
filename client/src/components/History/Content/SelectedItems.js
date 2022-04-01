/**
 * This component deals with item selection inside a history.
 * It allows to select individual items or perform a query selection.
 */

import { getFilters, testFilters } from "store/historyStore/historyItemsFiltering";

export default {
    props: {
        scopeKey: { type: String, required: true },
        getItemKey: { type: Function, required: true },
        filterText: { type: String, required: true },
    },
    data() {
        return {
            items: new Map(),
            showSelection: false,
            totalItemsInQuery: 0,
        };
    },
    computed: {
        selectionSize() {
            return this.isQuerySelection ? this.totalItemsInQuery : this.items.size;
        },
        isQuerySelection() {
            return this.totalItemsInQuery !== this.items.size;
        },
        currentFilters() {
            return getFilters(this.filterText);
        },
    },
    methods: {
        setShowSelection(val) {
            this.showSelection = val;
        },
        selectAllInCurrentQuery(loadedItems = [], totalItemsInQuery) {
            this.selectItems(loadedItems);
            this.totalItemsInQuery = totalItemsInQuery;
        },
        isSelected(item) {
            if (this.isQuerySelection) {
                return testFilters(this.currentFilters, item);
            }
            const key = this.getItemKey(item);
            return this.items.has(key);
        },
        setSelected(item, selected) {
            const key = this.getItemKey(item);
            const newSelected = new Map(this.items);
            selected ? newSelected.set(key, item) : newSelected.delete(key);
            this.items = newSelected;
            this.resetQuerySelection();
        },
        selectItems(items = []) {
            const newItems = [...this.items.values(), ...items];
            const newEntries = newItems.map((item) => {
                const key = this.getItemKey(item);
                return [key, item];
            });
            this.items = new Map(newEntries);
            this.resetQuerySelection();
        },
        resetQuerySelection() {
            this.totalItemsInQuery = this.items.size;
        },
        reset() {
            this.items = new Map();
            this.resetQuerySelection();
        },
    },
    watch: {
        scopeKey(newKey, oldKey) {
            if (newKey !== oldKey) {
                this.reset();
            }
        },
        selectionSize(newSize) {
            if (newSize > 0) {
                this.showSelection = true;
            }
        },
        showSelection(newVal) {
            if (!newVal) {
                this.reset();
            }
        },
    },
    render() {
        return this.$scopedSlots.default({
            selectedItems: this.items,
            showSelection: this.showSelection,
            isQuerySelection: this.isQuerySelection,
            selectionSize: this.selectionSize,
            setShowSelection: this.setShowSelection,
            selectAllInCurrentQuery: this.selectAllInCurrentQuery,
            selectItems: this.selectItems,
            isSelected: this.isSelected,
            setSelected: this.setSelected,
            resetSelection: this.reset,
        });
    },
};
