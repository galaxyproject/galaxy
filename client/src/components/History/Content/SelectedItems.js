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
        allItems: { type: Array, required: true },
    },
    data() {
        return {
            items: new Map(),
            showSelection: false,
            allSelected: false,
            initSelectedItem: null,
            initDirection: null,
            firstInRange: null,
            lastInRange: null,
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
        lastInRangeIndex() {
            return this.lastInRange ? this.allItems.indexOf(this.lastInRange) : null;
        },
        firstInRangeIndex() {
            return this.firstInRange ? this.allItems.indexOf(this.firstInRange) : null;
        },
        rangeSelectActive() {
            return this.lastInRange && this.initDirection;
        },
    },
    methods: {
        setShowSelection(val) {
            this.showSelection = val;
        },
        selectAllInCurrentQuery(force = true) {
            // if we are not forcing selectAll, and all items are already selected; deselect them
            if (!force && this.allSelected) {
                this.setShowSelection(false);
                return;
            }
            this.selectItems(this.allItems);
            this.allSelected = true;
        },
        isSelected(item) {
            if (this.isQuerySelection) {
                return HistoryFilters.testFilters(this.currentFilters, item);
            }
            const key = this.getItemKey(item);
            return this.items.has(key);
        },
        /** Adds/Removes an item from the selected items
         *
         * @param {Object} item - the item to be selected/deselected
         * @param {Boolean} selected - whether to select or deselect the item
         * @param {Boolean} checkInRange - whether to check if the item lies outside the range
         */
        setSelected(item, selected, checkInRange = true) {
            const key = this.getItemKey(item);
            const newSelected = new Map(this.items);
            selected ? newSelected.set(key, item) : newSelected.delete(key);
            this.items = newSelected;
            this.breakQuerySelection();

            // item selected from panel, range select is active, check if item lies outside the range
            if (checkInRange && this.rangeSelectActive) {
                const currentItemIndex = this.allItems.indexOf(item);

                /** If either of the following are `true`, change the range anchor */
                // if range select was downwards and the current item is below the lastInRange or above the firstInRange
                if (
                    this.initDirection === "ArrowDown" &&
                    (currentItemIndex > this.lastInRangeIndex || currentItemIndex < this.firstInRangeIndex)
                ) {
                    this.firstInRange = item;
                    this.lastInRange = item;
                }
                // if range select was upwards and the current item is above the lastInRange or below the firstInRange
                else if (
                    this.initDirection === "ArrowUp" &&
                    (currentItemIndex < this.lastInRangeIndex || currentItemIndex > this.firstInRangeIndex)
                ) {
                    this.firstInRange = item;
                    this.lastInRange = item;
                }
            }
        },
        /** Selecting items using `Shift+ArrowUp/ArrowDown` keys */
        shiftArrowKeySelect(item, nextItem, eventKey) {
            const currentItemKey = this.getItemKey(item);
            if (!this.initSelectedKey) {
                this.initSelectedItem = item;
                this.initDirection = eventKey;
                this.setSelected(item, true, false);
            }
            // got back to the initial selected item
            else if (this.initSelectedKey === currentItemKey) {
                this.initDirection = eventKey;
            }
            // same direction
            else if (this.initDirection === eventKey) {
                this.setSelected(item, true, false);
            }
            // different direction
            else {
                this.setSelected(item, false, false);
            }
            if (nextItem) {
                this.setSelected(nextItem, true, false);
            }
        },
        /** Range selecting items using `Shift+Click` */
        rangeSelect(item, prevItem) {
            if (prevItem && item) {
                // either a range select is not active or we have modified a range select (changing the anchor)
                const noRangeSelectOrModified = !this.initSelectedKey;
                if (noRangeSelectOrModified) {
                    // there is a range select active
                    if (this.rangeSelectActive) {
                        const currentItemIndex = this.allItems.indexOf(item);

                        // the current item is outside the range in the same direction;
                        // the new range will follow the last item in prev range
                        if (
                            (this.initDirection === "ArrowDown" && currentItemIndex > this.lastInRangeIndex) ||
                            (this.initDirection === "ArrowUp" && currentItemIndex < this.lastInRangeIndex)
                        ) {
                            this.initSelectedItem = this.lastInRange;
                        }
                        // the current item is outside the range in the opposite direction;
                        // the new range will follow the first item in prev range
                        else if (
                            (this.initDirection === "ArrowDown" && currentItemIndex < this.firstInRangeIndex) ||
                            (this.initDirection === "ArrowUp" && currentItemIndex > this.firstInRangeIndex)
                        ) {
                            this.initSelectedItem = this.firstInRange;
                        } else {
                            this.initSelectedItem = prevItem;
                            this.firstInRange = prevItem;
                        }
                    }
                    // there is no range select active
                    else {
                        // we are staring a new shift+click rangeSelect from `prevItem`
                        this.initSelectedItem = prevItem;
                        this.firstInRange = prevItem;
                    }
                }

                const initItemIndex = this.allItems.indexOf(this.initSelectedItem);
                const currentItemIndex = this.allItems.indexOf(item);

                const lastDirection = this.initDirection;
                let selections = [];
                // from allItems, get the items between the init item and the current item
                if (initItemIndex < currentItemIndex) {
                    this.initDirection = "ArrowDown";
                    selections = this.allItems.slice(initItemIndex + 1, currentItemIndex + 1);
                } else if (initItemIndex > currentItemIndex) {
                    this.initDirection = "ArrowUp";
                    selections = this.allItems.slice(currentItemIndex, initItemIndex);
                }

                let deselections;
                // there is an existing range select; deselect items in certain conditions
                if (this.rangeSelectActive) {
                    // if there is an active, uninterrupted range-select and the direction changed;
                    // deselect the items between the lastInRange and initSelectedItem
                    if (!noRangeSelectOrModified && lastDirection && lastDirection !== this.initDirection) {
                        if (this.lastInRangeIndex >= initItemIndex) {
                            deselections = this.allItems.slice(initItemIndex + 1, this.lastInRangeIndex + 1);
                        } else {
                            deselections = this.allItems.slice(this.lastInRangeIndex, initItemIndex);
                        }
                    }

                    // if the range has become smaller, deselect items between the lastInRange and the current item
                    else if (this.lastInRangeIndex < currentItemIndex && this.initDirection === "ArrowUp") {
                        deselections = this.allItems.slice(this.lastInRangeIndex, currentItemIndex);
                    } else if (this.lastInRangeIndex > currentItemIndex && this.initDirection === "ArrowDown") {
                        deselections = this.allItems.slice(currentItemIndex + 1, this.lastInRangeIndex + 1);
                    }
                }

                this.selectItems(selections);
                if (deselections) {
                    deselections.forEach((deselected) => this.setSelected(deselected, false, false));
                }
            } else {
                this.setSelected(item, true);
            }
            this.lastInRange = item;
        },
        /** Resets the initial item in a range select (or shiftArrowKeySelect) */
        initKeySelection() {
            this.initSelectedItem = null;
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
            this.lastInRange = null;
            this.firstInRange = null;
            this.initDirection = null;
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
            rangeSelect: this.rangeSelect,
            isSelected: this.isSelected,
            setSelected: this.setSelected,
            resetSelection: this.reset,
            shiftArrowKeySelect: this.shiftArrowKeySelect,
            initKeySelection: this.initKeySelection,
            initSelectedItem: this.initSelectedItem,
        });
    },
};
