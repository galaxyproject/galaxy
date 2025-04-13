import { computed, ref, watch } from "vue";

import { useEventStore } from "@/stores/eventStore";

import { useActiveElement } from "../useActiveElement";
import type { ComponentInstanceExtends, ComponentInstanceRef, SelectedItemsProps } from "./types";

/** A composable that allows for the selection of items in a list using keyboard and mouse
 * events, as well as navigating that list using keyboard events. */
export function useSelectedItems<T, ComponentType extends ComponentInstanceExtends>({
    scopeKey,
    getItemKey,
    filterText,
    totalItemsInQuery,
    allItems,
    filterClass,
    selectable,
    querySelectionBreak = () => {},
    onDelete,
    expectedKeyDownClass = undefined,
    disallowedKeyDownClasses = [],
    attributeForRangeSelection = "id",
    getAttributeForRangeSelection = (item: T) => getItemKey(item),
}: SelectedItemsProps<T>) {
    const eventStore = useEventStore();

    const selectedItems = ref<Map<string, T>>(new Map());
    const showSelection = ref(false);
    const allSelected = ref(false);
    const initSelectedItem = ref<T>();
    const initDirection = ref<string | null>(null);
    const firstInRange = ref<T>();
    const lastInRange = ref<T>();
    const lastItemId = ref<string | null>(null);

    const currItemFocused = useActiveElement();

    const selectionSize = computed(() => (isQuerySelection.value ? totalItemsInQuery.value : selectedItems.value.size));
    const isQuerySelection = computed(() => allSelected.value && totalItemsInQuery.value !== selectedItems.value.size);
    const currentFilters = computed(() => filterClass.getFiltersForText(filterText.value));
    const initSelectedKey = computed(() => (initSelectedItem.value ? getItemKey(initSelectedItem.value as T) : null)); // TODO: Weird Unwrap ref type
    const lastInRangeIndex = computed(() =>
        lastInRange.value ? allItems.value.indexOf(lastInRange.value as T) : null
    );
    const firstInRangeIndex = computed(() =>
        firstInRange.value ? allItems.value.indexOf(firstInRange.value as T) : null
    );
    const rangeSelectActive = computed(() => lastInRange.value && initDirection.value);

    const lastItemFocused = computed(() => {
        return lastItemId.value ? allItems.value.find((item) => lastItemId.value === getItemKey(item)) : null;
    });

    function setShowSelection(val: boolean) {
        showSelection.value = val;
    }

    function selectAllInCurrentQuery(force = true) {
        // if we are not forcing selectAll, and all items are already selected; deselect them
        if (!force && allSelected.value) {
            setShowSelection(false);
            return;
        }
        selectItems(allItems.value);
        allSelected.value = true;
    }

    function isSelected(item: T) {
        if (isQuerySelection.value) {
            return filterClass.testFilters(currentFilters.value, item as Record<string, unknown>);
        }
        const key = getItemKey(item as T);
        return selectedItems.value.has(key);
    }

    /** Adds/Removes an item from the selected items
     *
     * @param item - the item to be selected/deselected
     * @param selected - whether to select or deselect the item
     * @param checkInRange - whether to check if the item lies outside the range
     */
    function setSelected(item: T, selected: boolean, checkInRange = true) {
        const key = getItemKey(item as T);
        const newSelected = new Map(selectedItems.value);
        selected ? newSelected.set(key, item) : newSelected.delete(key);
        selectedItems.value = newSelected;
        breakQuerySelection();

        // item selected from panel, range select is active, check if item lies outside the range
        if (checkInRange && rangeSelectActive.value) {
            const currentItemIndex = allItems.value.indexOf(item as T);

            /** If either of the following are `true`, change the range anchor */
            // if range select was downwards and the current item is below the lastInRange or above the firstInRange
            if (
                initDirection.value === "ArrowDown" &&
                ((lastInRangeIndex.value !== null && currentItemIndex > lastInRangeIndex.value) ||
                    (firstInRangeIndex.value !== null && currentItemIndex < firstInRangeIndex.value))
            ) {
                firstInRange.value = item;
                lastInRange.value = item;
            }
            // if range select was upwards and the current item is above the lastInRange or below the firstInRange
            else if (
                initDirection.value === "ArrowUp" &&
                ((lastInRangeIndex.value !== null && currentItemIndex < lastInRangeIndex.value) ||
                    (firstInRangeIndex.value !== null && currentItemIndex > firstInRangeIndex.value))
            ) {
                firstInRange.value = item;
                lastInRange.value = item;
            }
        }
    }

    /** Selecting items using `Shift+ArrowUp/ArrowDown` keys */
    function shiftArrowKeySelect(item: T, nextItem: T | null, eventKey: string) {
        const currentItemKey = getItemKey(item as T);
        if (!initSelectedKey.value) {
            initSelectedItem.value = item;
            initDirection.value = eventKey;
            setSelected(item, true, false);
        }
        // got back to the initial selected item
        else if (initSelectedKey.value === currentItemKey) {
            initDirection.value = eventKey;
        }
        // same direction
        else if (initDirection.value === eventKey) {
            setSelected(item, true, false);
        }
        // different direction
        else {
            setSelected(item, false, false);
        }
        if (nextItem) {
            setSelected(nextItem, true, false);
        }
    }

    /** Range selecting items using `Shift+Click` */
    function rangeSelect(item: T, prevItem: T | null) {
        if (prevItem && item) {
            // either a range select is not active or we have modified a range select (changing the anchor)
            const noRangeSelectOrModified = !initSelectedKey.value;
            if (noRangeSelectOrModified) {
                // there is a range select active
                if (rangeSelectActive.value) {
                    const currentItemIndex = allItems.value.indexOf(item as T);

                    // the current item is outside the range in the same direction;
                    // the new range will follow the last item in prev range
                    if (
                        lastInRangeIndex.value !== null &&
                        ((initDirection.value === "ArrowDown" && currentItemIndex > lastInRangeIndex.value) ||
                            (initDirection.value === "ArrowUp" && currentItemIndex < lastInRangeIndex.value))
                    ) {
                        initSelectedItem.value = lastInRange.value;
                    }
                    // the current item is outside the range in the opposite direction;
                    // the new range will follow the first item in prev range
                    else if (
                        firstInRangeIndex.value !== null &&
                        ((initDirection.value === "ArrowDown" && currentItemIndex < firstInRangeIndex.value) ||
                            (initDirection.value === "ArrowUp" && currentItemIndex > firstInRangeIndex.value))
                    ) {
                        initSelectedItem.value = firstInRange.value;
                    } else {
                        initSelectedItem.value = prevItem;
                        firstInRange.value = prevItem;
                    }
                }
                // there is no range select active
                else {
                    // we are staring a new shift+click rangeSelect from `prevItem`
                    initSelectedItem.value = prevItem;
                    firstInRange.value = prevItem;
                }
            }

            const initItemIndex = allItems.value.indexOf(initSelectedItem.value as T);
            const currentItemIndex = allItems.value.indexOf(item as T);

            const lastDirection = initDirection.value;
            let selections: T[] = [];
            // from allItems, get the items between the init item and the current item
            if (initItemIndex < currentItemIndex) {
                initDirection.value = "ArrowDown";
                selections = allItems.value.slice(initItemIndex + 1, currentItemIndex + 1);
            } else if (initItemIndex > currentItemIndex) {
                initDirection.value = "ArrowUp";
                selections = allItems.value.slice(currentItemIndex, initItemIndex);
            }

            let deselections;
            // there is an existing range select; deselect items in certain conditions
            if (rangeSelectActive.value && lastInRangeIndex.value !== null) {
                // if there is an active, uninterrupted range-select and the direction changed;
                // deselect the items between the lastInRange and initSelectedItem
                if (!noRangeSelectOrModified && lastDirection && lastDirection !== initDirection.value) {
                    if (lastInRangeIndex.value >= initItemIndex) {
                        deselections = allItems.value.slice(initItemIndex + 1, lastInRangeIndex.value + 1);
                    } else {
                        deselections = allItems.value.slice(lastInRangeIndex.value, initItemIndex);
                    }
                }

                // if the range has become smaller, deselect items between the lastInRange and the current item
                else if (lastInRangeIndex.value < currentItemIndex && initDirection.value === "ArrowUp") {
                    deselections = allItems.value.slice(lastInRangeIndex.value, currentItemIndex);
                } else if (lastInRangeIndex.value > currentItemIndex && initDirection.value === "ArrowDown") {
                    deselections = allItems.value.slice(currentItemIndex + 1, lastInRangeIndex.value + 1);
                }
            }

            selectItems(selections);
            if (deselections) {
                deselections.forEach((deselected) => setSelected(deselected, false, false));
            }
        } else {
            setSelected(item, true);
        }
        lastInRange.value = item;
    }

    function isRangeSelectAnchor(item: T) {
        return Boolean(initSelectedItem.value && getItemKey(item) === getItemKey(initSelectedItem.value));
    }

    /** Resets the initial item in a range select (or shiftArrowKeySelect) */
    function initKeySelection() {
        initSelectedItem.value = undefined;
    }

    function selectItems(itemsToSelect: T[]) {
        const newItems = [...selectedItems.value.values(), ...itemsToSelect];
        const newEntries: Array<[string, T]> = newItems.map((item) => {
            const key = getItemKey(item as T);
            return [key, item];
        });
        selectedItems.value = new Map(newEntries);
        breakQuerySelection();
    }

    function breakQuerySelection() {
        if (allSelected.value) {
            querySelectionBreak();
        }
        allSelected.value = false;
    }

    function resetSelection() {
        selectedItems.value = new Map();
        allSelected.value = false;
        initKeySelection();
        lastInRange.value = undefined;
        firstInRange.value = undefined;
        initDirection.value = null;
        lastItemId.value = null;
    }

    // Define refs for component instances
    const itemRefs = computed<ComponentInstanceRef<ComponentType>>(() => {
        return allItems.value.reduce((acc, item) => {
            acc[getItemKey(item)] = ref(null);
            return acc;
        }, {} as ComponentInstanceRef<ComponentType>);
    });

    function findFirstFocusable(itemRef: InstanceType<ComponentType> | null | undefined): HTMLElement | null {
        if (!itemRef) {
            return null;
        }

        // If itemRef is a component instance with $el, check if it's focusable
        if ("$el" in itemRef) {
            if (itemRef.$el && typeof itemRef.$el.focus === "function") {
                return itemRef.$el;
            }
        }
        // If itemRef is an array, recursively check its elements
        else if (Array.isArray(itemRef)) {
            for (const element of itemRef as unknown[]) {
                const focusable = findFirstFocusable(element as InstanceType<ComponentType>);
                if (focusable) {
                    return focusable;
                }
            }
        }
        // If itemRef is a DOM element, check if it's focusable
        else if (typeof itemRef.focus === "function") {
            return itemRef;
        }

        // If no focusable element is found, return null
        return null;
    }

    function arrowNavigate(item: T, eventKey: string) {
        let nextItem = null;
        if (eventKey === "ArrowDown") {
            nextItem = allItems.value[allItems.value.indexOf(item) + 1];
        } else if (eventKey === "ArrowUp") {
            nextItem = allItems.value[allItems.value.indexOf(item) - 1];
        }
        if (nextItem) {
            const itemRef = itemRefs.value[getItemKey(nextItem)]?.value;
            const focusableElement = findFirstFocusable(itemRef);
            if (focusableElement) {
                focusableElement.focus();
            }
        }
        return nextItem ?? null;
    }

    function onKeyDown(item: T, event: KeyboardEvent) {
        if (!validateClassList((event.target as HTMLElement)?.classList)) {
            return;
        }

        if ((event.key === "ArrowUp" || event.key === "ArrowDown") && !event.shiftKey) {
            event.preventDefault();
            arrowNavigate(item, event.key);
        }

        if (selectable.value) {
            if (event.key === "Tab") {
                initKeySelection();
            } else {
                event.preventDefault();
                if ((event.key === "ArrowUp" || event.key === "ArrowDown") && event.shiftKey) {
                    shiftArrowKeySelect(item, arrowNavigate(item, event.key), event.key);
                } else if (event.key === "ArrowUp" || event.key === "ArrowDown") {
                    initKeySelection();
                } else if (
                    item &&
                    event.key === "Delete" &&
                    !isSelected(item) &&
                    typeof item === "object" &&
                    "deleted" in item &&
                    !item.deleted
                ) {
                    onDelete(item, event.shiftKey);
                    setSelected(item, false);
                    initKeySelection();
                    arrowNavigate(item, "ArrowDown");
                } else if (event.key === "Escape") {
                    (event.target as HTMLElement)?.blur();
                } else if (event.key === "a" && eventStore.isCtrlKey(event)) {
                    selectAllInCurrentQuery(false);
                }
            }
        }
    }

    /** Click handler for selectable items
     * @returns `true` if after the click, more click handling is needed
     */
    function onClick(item: T, e: Event): boolean {
        const event = e as KeyboardEvent;
        if (selectable.value) {
            if (eventStore.isCtrlKey(event)) {
                initKeySelection();
                setSelected(item, !isSelected(item));
                return false;
            } else if (event.shiftKey) {
                rangeSelect(item, lastItemFocused.value ?? null);
                return false;
            } else {
                initKeySelection();
                return true;
            }
        }
        return true;
    }

    /** If the event target does not match the expected class, or contains a disallowed class, ignore the event. */
    function validateClassList(classList: DOMTokenList) {
        if (
            (expectedKeyDownClass && !classList.contains(expectedKeyDownClass)) ||
            (disallowedKeyDownClasses && disallowedKeyDownClasses.some((className) => classList.contains(className)))
        ) {
            return false;
        }
        return true;
    }

    function resetFocusToOffset(offset: number) {
        const itemAtOffset = allItems.value[offset];
        if (itemAtOffset) {
            const itemElement = itemRefs.value[getItemKey(itemAtOffset)]?.value?.$el as HTMLElement;
            itemElement?.focus();
        }
    }

    watch(
        () => currItemFocused.value,
        (newItem, oldItem) => {
            // if user clicked elsewhere, set lastItemId to the last focused item
            const lastExpectedParent = oldItem?.closest(`.${expectedKeyDownClass}`);

            if (newItem) {
                let lastElement: Element | null = null;
                if (oldItem && validateClassList(oldItem.classList)) {
                    lastElement = oldItem;
                } else if (lastExpectedParent && validateClassList(lastExpectedParent.classList)) {
                    lastElement = lastExpectedParent;
                }
                const lastItem = lastElement
                    ? allItems.value.find(
                          (item) =>
                              lastElement.getAttribute(attributeForRangeSelection) ===
                              getAttributeForRangeSelection(item)
                      )
                    : null;
                lastItemId.value = lastItem ? getItemKey(lastItem) : null;
            }
        }
    );

    watch(scopeKey, (newKey, oldKey) => {
        if (newKey !== oldKey) {
            setShowSelection(false);
        }
    });

    watch(selectionSize, (newSize) => {
        if (newSize > 0) {
            setShowSelection(true);
        }
    });

    watch(showSelection, (newVal) => {
        if (!newVal) {
            resetSelection();
        }
    });

    watch(totalItemsInQuery, (newVal, oldVal) => {
        if (allSelected.value && newVal !== oldVal) {
            breakQuerySelection();
        }
    });

    return {
        selectedItems,
        showSelection,
        selectionSize,
        initSelectedItem,
        isQuerySelection,
        itemRefs,
        arrowNavigate,
        setShowSelection,
        selectAllInCurrentQuery,
        selectItems,
        rangeSelect,
        onClick,
        onKeyDown,
        isRangeSelectAnchor,
        isSelected,
        setSelected,
        resetSelection,
        shiftArrowKeySelect,
        initKeySelection,
        resetFocusToOffset,
    };
}
