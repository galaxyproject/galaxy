/**
 * This component deals with item selection inside a history.
 * It allows to select individual items or perform a query selection.
 */

import { HistoryFilters } from "../HistoryFilters";

export default {
    props: {
        scopeKey: { type: String, required: true },
        getItemKey: { type: Function, required: true },
        filterText: { type: String, required: true },
        totalItemsInQuery: { type: Number, required: false },
    },
    data() {
        return {
            items: new Map(),
            showSelection: false,
            allSelected: false,
            initSelectedItem: null,
            initDirection: null,
        };
    },
    computed: {
        selectionSize() {
            return this.isQuerySelection ? this.totalItemsInQuery : this.items.size;
        },
        isQuerySelection() {
            return this.allSelected && this.totalItemsInQuery !== this.items.size;
        },
        currentFilters() {
            return HistoryFilters.getFiltersForText(this.filterText);
        },
        initSelectedKey() {
            return this.initSelectedItem ? this.getItemKey(this.initSelectedItem) : null;
        },
    },
    methods: {
        setShowSelection(val) {
            this.showSelection = val;
        },
        selectAllInCurrentQuery(loadedItems = [], force = true) {
            // if we are not forcing selectAll, and all items are already selected; deselect them
            if (!force && this.allSelected) {
                this.setShowSelection(false);
                return;
            }
            this.selectItems(loadedItems);
            this.allSelected = true;
        },
        isSelected(item) {
            if (this.isQuerySelection) {
                return HistoryFilters.testFilters(this.currentFilters, item);
            }
            const key = this.getItemKey(item);
            return this.items.has(key);
        },
        setSelected(item, selected) {
            const key = this.getItemKey(item);
            const newSelected = new Map(this.items);
            selected ? newSelected.set(key, item) : newSelected.delete(key);
            this.items = newSelected;
            this.breakQuerySelection();
        },
        shiftSelect(item, nextItem, eventKey) {
            const currentItemKey = this.getItemKey(item);
            if (!this.initSelectedKey) {
                this.initSelectedItem = item;
                this.initDirection = eventKey;
                this.setSelected(item, true);
            }
            // got back to the initial selected item
            else if (this.initSelectedKey === currentItemKey) {
                this.initDirection = eventKey;
            }
            // same direction
            else if (this.initDirection === eventKey) {
                this.setSelected(item, true);
            }
            // different direction
            else {
                this.setSelected(item, false);
            }
            if (nextItem) {
                this.setSelected(nextItem, true);
            }
        },
        selectTo(item, prevItem, allItems, reset = true) {
            if (prevItem && item) {
                // we are staring a new shift+click selectTo from `prevItem`
                if (!this.initSelectedKey) {
                    this.initSelectedItem = prevItem;
                }

                // `reset = false` in the case user is holding shift+ctrl key
                if (reset) {
                    // clear this.items of any other selections
                    this.items = new Map();
                }
                this.setSelected(this.initSelectedItem, true);

                const initItemIndex = allItems.indexOf(this.initSelectedItem);
                const currentItemIndex = allItems.indexOf(item);

                let selections = [];
                // from allItems, get the items between the init item and the current item
                if (initItemIndex < currentItemIndex) {
                    this.initDirection = "ArrowDown";
                    selections = allItems.slice(initItemIndex + 1, currentItemIndex + 1);
                } else if (initItemIndex > currentItemIndex) {
                    this.initDirection = "ArrowUp";
                    selections = allItems.slice(currentItemIndex, initItemIndex);
                }
                this.selectItems(selections);
            } else {
                this.setSelected(item, true);
            }
        },
        initKeySelection() {
            this.initSelectedItem = null;
            this.initDirection = null;
        },
        selectItems(items = []) {
            const newItems = [...this.items.values(), ...items];
            const newEntries = newItems.map((item) => {
                const key = this.getItemKey(item);
                return [key, item];
            });
            this.items = new Map(newEntries);
            this.breakQuerySelection();
        },
        breakQuerySelection() {
            if (this.allSelected) {
                this.$emit("query-selection-break");
            }
            this.allSelected = false;
        },
        reset() {
            this.items = new Map();
            this.allSelected = false;
            this.initKeySelection();
        },
        cancelSelection() {
            this.showSelection = false;
        },
    },
    watch: {
        scopeKey(newKey, oldKey) {
            if (newKey !== oldKey) {
                this.cancelSelection();
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
        totalItemsInQuery(newVal, oldVal) {
            if (this.allSelected && newVal !== oldVal) {
                this.breakQuerySelection();
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
            selectTo: this.selectTo,
            isSelected: this.isSelected,
            setSelected: this.setSelected,
            resetSelection: this.reset,
            shiftSelect: this.shiftSelect,
            initKeySelection: this.initKeySelection,
        });
    },
};
