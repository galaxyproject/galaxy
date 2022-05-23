import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "jest/helpers";
import SelectedItems from "./SelectedItems";

const localVue = getLocalVue();

const DEFAULT_PROPS = {
    scopeKey: "scope",
    getItemKey: (item) => `item-key-${item.id}`,
    filterText: "",
    totalItemsInQuery: 100,
};

describe("History SelectedItems", () => {
    let wrapper;
    let slotProps;

    beforeEach(async () => {
        wrapper = shallowMount(SelectedItems, {
            localVue,
            propsData: DEFAULT_PROPS,
            scopedSlots: {
                default(props) {
                    slotProps = props;
                },
            },
        });
        await flushPromises();
    });

    afterEach(async () => {
        if (wrapper) {
            await wrapper.destroy();
        }
    });

    it("should be able to enable/disable selection mode", async () => {
        expectSelectionDisabled();

        await enableSelection();
        expectSelectionEnabled();

        await disableSelection();
        expectSelectionDisabled();
    });

    it("should discard the current selection when disabling the selection", async () => {
        const numberOfExpectedItems = 3;
        await selectSomeItemsManually(numberOfExpectedItems);
        expect(slotProps.selectionSize).toBe(numberOfExpectedItems);

        await disableSelection();
        expectSelectionDisabled();
    });

    it("should disable/discard the current selection when the `scopeKey` changes", async () => {
        const numberOfExpectedItems = 3;
        await selectSomeItemsManually(numberOfExpectedItems);
        expect(slotProps.selectionSize).toBe(numberOfExpectedItems);

        await wrapper.setProps({ scopeKey: "different-scope" });

        expectSelectionDisabled();
    });

    it("should discard (but not disable) the current selection on `reset`", async () => {
        const numberOfExpectedItems = 3;
        await selectSomeItemsManually(numberOfExpectedItems);
        expect(slotProps.selectionSize).toBe(numberOfExpectedItems);

        await resetSelection();

        expect(slotProps.selectionSize).toBe(0);
        expectSelectionEnabled();
    });

    describe("Query Selection Mode", () => {
        it("is considered a query selection when we select `all items` and the query contains more items than we have currently loaded", async () => {
            const expectedTotalItemsInQuery = 100;
            const numberOfLoadedItems = 10;
            const loadedItems = generateTestItems(numberOfLoadedItems);

            await selectAllItemsInCurrentQuery(loadedItems);

            expect(slotProps.isQuerySelection).toBe(true);
            expect(slotProps.selectionSize).toBe(expectedTotalItemsInQuery);
        });

        it("shouldn't be a query selection when we already have all items loaded", async () => {
            const expectedTotalItemsInQuery = 10;
            const numberOfLoadedItems = 10;
            const loadedItems = generateTestItems(numberOfLoadedItems);
            await wrapper.setProps({ totalItemsInQuery: expectedTotalItemsInQuery });

            await selectAllItemsInCurrentQuery(loadedItems);

            expect(slotProps.isQuerySelection).toBe(false);
            expect(slotProps.selectionSize).toBe(expectedTotalItemsInQuery);
        });

        it("should `break` query selection mode when we unselect an item", async () => {
            const expectedTotalItemsInQuery = 100;
            const numberOfLoadedItems = 10;
            const loadedItems = generateTestItems(numberOfLoadedItems);
            await selectAllItemsInCurrentQuery(loadedItems);
            expect(slotProps.isQuerySelection).toBe(true);
            expect(slotProps.selectionSize).toBe(expectedTotalItemsInQuery);
            expect(wrapper.emitted()["query-selection-break"]).toBeUndefined();

            await unselectItem(loadedItems[0]);

            expect(slotProps.isQuerySelection).toBe(false);
            expect(slotProps.selectionSize).toBe(numberOfLoadedItems - 1);
            expect(wrapper.emitted()["query-selection-break"]).toBeDefined();
        });

        it("should `break` query selection mode when the total number of items changes", async () => {
            const numberOfLoadedItems = 10;
            const loadedItems = generateTestItems(numberOfLoadedItems);
            await selectAllItemsInCurrentQuery(loadedItems);
            expect(slotProps.isQuerySelection).toBe(true);
            expect(wrapper.emitted()["query-selection-break"]).toBeUndefined();

            await wrapper.setProps({ totalItemsInQuery: 80 });

            expect(slotProps.isQuerySelection).toBe(false);
            expect(slotProps.selectionSize).toBe(numberOfLoadedItems);
            expect(wrapper.emitted()["query-selection-break"]).toBeDefined();
        });
    });

    describe("Selection Size", () => {
        it("should match the number of items explicitly selected (non query)", async () => {
            const numberOfExpectedItems = 3;
            const items = generateTestItems(numberOfExpectedItems);
            await selectItems(items);
            expect(slotProps.isQuerySelection).toBe(false);
            expect(slotProps.selectionSize).toBe(numberOfExpectedItems);

            await unselectItem(items[0]);

            expect(slotProps.selectionSize).toBe(numberOfExpectedItems - 1);
        });

        it("should match the number of items in query when selecting all items", async () => {
            const expectedTotalItemsInQuery = 100;
            const loadedItems = []; // Even if there are no explicit items selected
            await selectAllItemsInCurrentQuery(loadedItems);
            expect(slotProps.isQuerySelection).toBe(true);
            expect(slotProps.selectionSize).toBe(expectedTotalItemsInQuery);
        });
    });

    async function enableSelection() {
        const { setShowSelection } = slotProps;
        expect(setShowSelection).toBeInstanceOf(Function);
        await setShowSelection(true);
    }

    async function disableSelection() {
        const { setShowSelection } = slotProps;
        expect(setShowSelection).toBeInstanceOf(Function);
        await setShowSelection(false);
    }

    async function selectItems(items) {
        const { selectItems } = slotProps;
        expect(selectItems).toBeInstanceOf(Function);

        await selectItems(items);
    }

    async function selectSomeItemsManually(numberOfItems) {
        const items = generateTestItems(numberOfItems);
        await selectItems(items);
    }

    async function unselectItem(item) {
        const { setSelected } = slotProps;
        expect(setSelected).toBeInstanceOf(Function);
        await setSelected(item, false);
    }

    async function resetSelection() {
        const { resetSelection } = slotProps;
        expect(resetSelection).toBeInstanceOf(Function);
        resetSelection();
    }

    async function selectAllItemsInCurrentQuery(loadedItems) {
        const { selectAllInCurrentQuery } = slotProps;
        expect(selectAllInCurrentQuery).toBeInstanceOf(Function);

        await selectAllInCurrentQuery(loadedItems);
    }

    function generateTestItems(numberOfItems) {
        return Array.from({ length: numberOfItems }, (_, i) => {
            return {
                id: i,
            };
        });
    }

    function expectSelectionDisabled() {
        expect(slotProps.showSelection).toBe(false);
        expectNothingSelected();
    }

    function expectSelectionEnabled() {
        expect(slotProps.showSelection).toBe(true);
    }

    function expectNothingSelected() {
        expect(slotProps.selectionSize).toBe(0);
        expect(slotProps.selectedItems.size).toEqual(slotProps.selectionSize);
        expect(slotProps.isQuerySelection).toBe(false);
    }
});
