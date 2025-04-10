import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { ref } from "vue";

import { HistoryFilters } from "@/components/History/HistoryFilters";

import { useSelectedItems } from "./selectedItems";

describe("useSelectedItems", () => {
    let selectionReturn: ReturnType<typeof useSelectedItems<{ id: number }, any>>;

    const numberOfLoadedItems = 10;
    const allItems = generateTestItems(numberOfLoadedItems);
    const DEFAULT_PROPS = {
        scopeKey: ref("scope"),
        getItemKey: getItemKey,
        filterText: ref(""),
        totalItemsInQuery: ref(numberOfLoadedItems),
        allItems: ref(allItems),
        filterClass: HistoryFilters,
        selectable: ref(true),
        onDelete: () => {},
    };

    beforeEach(async () => {
        setActivePinia(createPinia());
        selectionReturn = useSelectedItems<{ id: number }, any>(DEFAULT_PROPS);
        await flushPromises();

        // We need to enable selection first; note that this is not an enforced behavior for this composable
        // but the HistoryPanel uses the `showSelection` ref to determine if it should show the selection
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

        DEFAULT_PROPS.scopeKey.value = "different-scope";
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

    // describe("Query Selection Mode", () => {
    //     it("is considered a query selection when we select `all items` and the query contains more items than we have currently loaded", async () => {
    //         const expectedTotalItemsInQuery = 100;
    //         DEFAULT_PROPS.totalItemsInQuery.value = expectedTotalItemsInQuery;

    //         await selectAllItemsInCurrentQuery();

    //         expect(selectionReturn.isQuerySelection.value).toBe(true);
    //         expect(selectionReturn.selectionSize.value).toBe(expectedTotalItemsInQuery);
    //     });

    //     it("shouldn't be a query selection when we already have all items loaded", async () => {
    //         const expectedTotalItemsInQuery = 10;
    //         DEFAULT_PROPS.totalItemsInQuery.value = expectedTotalItemsInQuery;

    //         await selectAllItemsInCurrentQuery();

    //         expect(selectionReturn.isQuerySelection.value).toBe(false);
    //         expect(selectionReturn.selectionSize.value).toBe(expectedTotalItemsInQuery);
    //     });

    //     it("should `break` query selection mode when we unselect an item", async () => {
    //         const expectedTotalItemsInQuery = 100;
    //         await selectAllItemsInCurrentQuery();
    //         expect(selectionReturn.isQuerySelection.value).toBe(true);
    //         expect(selectionReturn.selectionSize.value).toBe(expectedTotalItemsInQuery);
    //         // expect(composable.emitted()["query-selection-break"]).toBeUndefined(); // TODO

    //         await unselectItem(allItems[0]);

    //         expect(selectionReturn.isQuerySelection.value).toBe(false);
    //         expect(selectionReturn.selectionSize.value).toBe(numberOfLoadedItems - 1);
    //         // expect(composable.emitted()["query-selection-break"]).toBeDefined(); // TODO
    //     });

    //     it("should `break` query selection mode when the total number of items changes", async () => {
    //         await selectAllItemsInCurrentQuery();
    //         expect(selectionReturn.isQuerySelection.value).toBe(true);
    //         // expect(composable.emitted()["query-selection-break"]).toBeUndefined(); // TODO

    //         DEFAULT_PROPS.totalItemsInQuery.value = 80;

    //         expect(selectionReturn.isQuerySelection.value).toBe(false);
    //         expect(selectionReturn.selectionSize.value).toBe(numberOfLoadedItems);
    //         // expect(composable.emitted()["query-selection-break"]).toBeDefined(); // TODO
    //     });
    // });

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

        // it("should match the number of items explicitly selected (non query)", async () => {
        //     const numberOfExpectedItems = 3;
        //     const items = generateTestItems(numberOfExpectedItems);
        //     selectItems(items);
        //     expect(selectionReturn.isQuerySelection.value).toBe(false);
        //     expect(selectionReturn.selectionSize.value).toBe(numberOfExpectedItems);

        //     await unselectItem(items[0]);

        //     expect(selectionReturn.selectionSize.value).toBe(numberOfExpectedItems - 1);
        // });

        // it("should match the number of items in query when selecting all items", async () => {
        //     const expectedTotalItemsInQuery = 100;
        //     DEFAULT_PROPS.allItems.value = generateTestItems(0); // Even if there are no explicit items selected
        //     await selectAllItemsInCurrentQuery();
        //     expect(selectionReturn.isQuerySelection.value).toBe(true);
        //     expect(selectionReturn.selectionSize.value).toBe(expectedTotalItemsInQuery);
        // });
    });

    function getItemKey(item: any) {
        return `item-key-${item.id}`;
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

    function selectItems(items: any[]) {
        const { selectItems } = selectionReturn;
        expect(selectItems).toBeInstanceOf(Function);

        selectItems(items);
    }

    async function selectSomeItemsManually(numberOfItems: number) {
        const items = generateTestItems(numberOfItems);
        selectItems(items);
        await flushPromises();
    }

    async function unselectItem(item: any) {
        const { setSelected } = selectionReturn;
        expect(setSelected).toBeInstanceOf(Function);
        await setSelected(item, false);
    }

    async function resetSelection() {
        const { resetSelection } = selectionReturn;
        expect(resetSelection).toBeInstanceOf(Function);
        resetSelection();
    }

    async function selectAllItemsInCurrentQuery(loadedItems: any[] = allItems) {
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
