import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { ref } from "vue";

import { HistoryFilters } from "@/components/History/HistoryFilters";

import { useSelectedItems } from "./selectedItems";

const querySelectionBreakMock = jest.fn();

type ItemType = { id: number };

describe("useSelectedItems", () => {
    let selectionReturn: ReturnType<typeof useSelectedItems<ItemType, any>>;

    const numberOfLoadedItems = 10;
    const allItems = generateTestItems(numberOfLoadedItems);
    const selectedItemsProps = {
        scopeKey: ref("scope"),
        getItemKey: getItemKey,
        filterText: ref(""),
        totalItemsInQuery: ref(numberOfLoadedItems),
        allItems: ref(allItems),
        filterClass: HistoryFilters, // Can be any, just to satisfy the type
        selectable: ref(true),
        querySelectionBreak: () => querySelectionBreakMock(),
        onDelete: () => {},
    };

    beforeEach(async () => {
        setActivePinia(createPinia());
        selectionReturn = useSelectedItems<ItemType, any>(selectedItemsProps);
        await flushPromises();

        // We need to enable selection first; note that this is not an enforced behavior for this composable
        // e.g.: the HistoryPanel uses the `showSelection` ref to determine if it should show the selection
        //       while the WorkflowList doesn't.
        enableSelection();
    });

    afterEach(() => {
        if (selectionReturn) {
            selectionReturn.resetSelection();
        }
    });

    it("should be able to enable/disable selection mode", async () => {
        // We enabled selection in the beforeEach
        expectSelectionEnabled();

        await disableSelection();
        expectSelectionDisabled();
    });

    it("should discard the current selection when disabling the selection", async () => {
        const numberOfExpectedItems = 3;
        await selectSomeItemsManually(numberOfExpectedItems);
        expect(selectionReturn.selectionSize.value).toBe(numberOfExpectedItems);

        await disableSelection();
        expectSelectionDisabled();
    });

    it("should disable/discard the current selection when the `scopeKey` changes", async () => {
        const numberOfExpectedItems = 3;
        await selectSomeItemsManually(numberOfExpectedItems);
        expect(selectionReturn.selectionSize.value).toBe(numberOfExpectedItems);

        selectedItemsProps.scopeKey.value = "different-scope";
        await flushPromises();

        expectSelectionDisabled();
    });

    it("should discard (but not disable) the current selection on `reset`", async () => {
        const numberOfExpectedItems = 3;
        await selectSomeItemsManually(numberOfExpectedItems);
        expect(selectionReturn.selectionSize.value).toBe(numberOfExpectedItems);

        await resetSelection();

        expect(selectionReturn.selectionSize.value).toBe(0);
        expectSelectionEnabled();
    });

    describe("Query Selection Mode", () => {
        it("is considered a query selection when we select `all items` and the query contains more items than we have currently loaded", async () => {
            const expectedTotalItemsInQuery = 100;
            await setTotalItemsInQuery(expectedTotalItemsInQuery);

            await selectAllItemsInCurrentQuery();

            expect(selectionReturn.isQuerySelection.value).toBe(true);
            expect(selectionReturn.selectionSize.value).toBe(expectedTotalItemsInQuery);
        });

        it("shouldn't be a query selection when we already have all items loaded", async () => {
            const expectedTotalItemsInQuery = 10;
            await setTotalItemsInQuery(expectedTotalItemsInQuery);

            await selectAllItemsInCurrentQuery();

            expect(selectionReturn.isQuerySelection.value).toBe(false);
            expect(selectionReturn.selectionSize.value).toBe(expectedTotalItemsInQuery);
        });

        it("should `break` query selection mode when we unselect an item", async () => {
            const expectedTotalItemsInQuery = 100;
            await setTotalItemsInQuery(expectedTotalItemsInQuery);

            await selectAllItemsInCurrentQuery();
            expect(selectionReturn.isQuerySelection.value).toBe(true);
            expect(selectionReturn.selectionSize.value).toBe(expectedTotalItemsInQuery);
            expect(querySelectionBreakMock).not.toHaveBeenCalled();

            if (!allItems.length || !allItems[0]) {
                throw new Error("allItems is empty or undefined");
            }

            selectionReturn.setSelected(allItems[0], false);

            expect(selectionReturn.isQuerySelection.value).toBe(false);
            expect(selectionReturn.selectionSize.value).toBe(numberOfLoadedItems - 1);
            expect(querySelectionBreakMock).toHaveBeenCalled();
        });

        it("should `break` query selection mode when the total number of items changes", async () => {
            await selectAllItemsInCurrentQuery();
            expect(selectionReturn.isQuerySelection.value).toBe(true);
            expect(querySelectionBreakMock).not.toHaveBeenCalled();

            selectedItemsProps.totalItemsInQuery.value = 80;
            await flushPromises();

            expect(selectionReturn.isQuerySelection.value).toBe(false);
            expect(selectionReturn.selectionSize.value).toBe(numberOfLoadedItems);
            expect(querySelectionBreakMock).toHaveBeenCalled();
        });
    });

    describe("Selection Size", () => {
        it("should select/unselect items correctly", async () => {
            expect(selectionReturn.selectedItems.value.size).toBe(0);

            if (allItems.length && allItems[0] && allItems[1]) {
                selectionReturn.setSelected(allItems[0], true);
                expect(selectionReturn.selectedItems.value.size).toBe(1);

                selectionReturn.setSelected(allItems[1], true);
                expect(selectionReturn.selectedItems.value.size).toBe(2);

                selectionReturn.setSelected(allItems[0], false);
                expect(selectionReturn.selectedItems.value.size).toBe(1);

                expect(selectionReturn.selectedItems.value.has(getItemKey(allItems[0]))).toBe(false);
                expect(selectionReturn.selectedItems.value.has(getItemKey(allItems[1]))).toBe(true);
            } else {
                throw new Error("allItems is empty or undefined");
            }
        });

        it("should match the number of items explicitly selected (non query)", async () => {
            const numberOfExpectedItems = 3;
            const items = generateTestItems(numberOfExpectedItems);
            selectItems(items);
            expect(selectionReturn.isQuerySelection.value).toBe(false);
            expect(selectionReturn.selectionSize.value).toBe(numberOfExpectedItems);

            if (!items.length || !items[0]) {
                throw new Error("items is empty or undefined");
            }
            selectionReturn.setSelected(items[0], false);

            expect(selectionReturn.selectionSize.value).toBe(numberOfExpectedItems - 1);
        });

        it("should match the number of items in query when selecting all items", async () => {
            const expectedTotalItemsInQuery = 100;
            await setTotalItemsInQuery(expectedTotalItemsInQuery);

            selectedItemsProps.allItems.value = generateTestItems(0); // Even if there are no explicit items selected
            await selectAllItemsInCurrentQuery();
            expect(selectionReturn.isQuerySelection.value).toBe(true);
            expect(selectionReturn.selectionSize.value).toBe(expectedTotalItemsInQuery);
        });
    });

    function getItemKey(item: ItemType) {
        return `item-key-${item.id}`;
    }

    async function setTotalItemsInQuery(totalItems: number) {
        selectedItemsProps.totalItemsInQuery.value = totalItems;
        await flushPromises();
    }

    function enableSelection() {
        const { setShowSelection } = selectionReturn;
        expect(setShowSelection).toBeInstanceOf(Function);
        setShowSelection(true);
    }

    async function disableSelection() {
        const { setShowSelection } = selectionReturn;
        expect(setShowSelection).toBeInstanceOf(Function);
        setShowSelection(false);
        await flushPromises();
    }

    function selectItems(items: ItemType[]) {
        const { selectItems } = selectionReturn;
        expect(selectItems).toBeInstanceOf(Function);

        selectItems(items);
    }

    async function selectSomeItemsManually(numberOfItems: number) {
        const items = generateTestItems(numberOfItems);
        selectItems(items);
        await flushPromises();
    }

    async function resetSelection() {
        const { resetSelection } = selectionReturn;
        expect(resetSelection).toBeInstanceOf(Function);
        resetSelection();
    }

    async function selectAllItemsInCurrentQuery() {
        const { selectAllInCurrentQuery } = selectionReturn;
        expect(selectAllInCurrentQuery).toBeInstanceOf(Function);

        selectAllInCurrentQuery();
        await flushPromises();
    }

    function generateTestItems(numberOfItems: number) {
        return Array.from({ length: numberOfItems }, (_, i) => {
            return {
                id: i,
            };
        });
    }

    function expectSelectionDisabled() {
        expect(selectionReturn.showSelection.value).toBe(false);
        expectNothingSelected();
    }

    function expectSelectionEnabled() {
        expect(selectionReturn.showSelection.value).toBe(true);
    }

    function expectNothingSelected() {
        expect(selectionReturn.selectionSize.value).toBe(0);
        expect(selectionReturn.selectedItems.value.size).toEqual(selectionReturn.selectionSize.value);
        expect(selectionReturn.isQuerySelection.value).toBe(false);
    }
});
