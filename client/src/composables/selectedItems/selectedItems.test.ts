import { nth } from "@tests/vitest/helpers";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type EffectScope, effectScope, nextTick, ref } from "vue";

import { HistoryFilters } from "@/components/History/HistoryFilters";

import { useSelectedItems } from "./selectedItems";
import type { ComponentInstanceExtends, SelectedItemsProps } from "./types";

type Item = { id: number };

const loadedItemCount = 10;
const getItemKey = (item: Item) => `item-key-${item.id}`;
const createItems = (count: number) => Array.from({ length: count }, (_, id) => ({ id }));

describe("useSelectedItems", () => {
    let props: SelectedItemsProps<Item>;
    let selection: ReturnType<typeof useSelectedItems<Item, ComponentInstanceExtends>>;
    let scope: EffectScope;
    const querySelectionBreak = vi.fn();

    beforeEach(() => {
        setActivePinia(createPinia());
        querySelectionBreak.mockClear();
        props = {
            scopeKey: ref("scope"),
            getItemKey,
            filterText: ref(""),
            totalItemsInQuery: ref(loadedItemCount),
            allItems: ref(createItems(loadedItemCount)),
            filterClass: HistoryFilters,
            selectable: ref(true),
            querySelectionBreak,
            onDelete: () => {},
        };
        scope = effectScope();
        scope.run(() => {
            selection = useSelectedItems<Item, ComponentInstanceExtends>(props);
        });
        selection.setShowSelection(true);
    });

    afterEach(() => scope.stop());

    it("exposes selection actions and can disable selection mode", async () => {
        expect(selection.setShowSelection).toBeInstanceOf(Function);
        expect(selection.selectItems).toBeInstanceOf(Function);
        expect(selection.resetSelection).toBeInstanceOf(Function);
        expect(selection.selectAllInCurrentQuery).toBeInstanceOf(Function);
        expect(selection.showSelection.value).toBe(true);

        selection.setShowSelection(false);
        await nextTick();

        expectSelectionDisabled();
    });

    it("clears selected items when selection mode is disabled", async () => {
        selection.selectItems(createItems(3));
        await nextTick();
        expect(selection.selectionSize.value).toBe(3);

        selection.setShowSelection(false);
        await nextTick();

        expectSelectionDisabled();
    });

    it("disables selection and clears selected items when the scope changes", async () => {
        selection.selectItems(createItems(3));
        await nextTick();
        expect(selection.selectionSize.value).toBe(3);

        props.scopeKey.value = "different-scope";
        await nextTick();

        expectSelectionDisabled();
    });

    it("clears selected items without disabling selection mode on reset", async () => {
        selection.selectItems(createItems(3));
        await nextTick();
        expect(selection.selectionSize.value).toBe(3);

        selection.resetSelection();

        expect(selection.selectionSize.value).toBe(0);
        expect(selection.showSelection.value).toBe(true);
    });

    describe("query selection", () => {
        it.each([
            { name: "counts all query items when more exist than are loaded", totalItems: 100, isQuerySelection: true },
            {
                name: "counts loaded items without query selection when all are loaded",
                totalItems: 10,
                isQuerySelection: false,
            },
        ])("$name", async ({ totalItems, isQuerySelection }) => {
            props.totalItemsInQuery.value = totalItems;
            await nextTick();

            selection.selectAllInCurrentQuery();
            await nextTick();

            expect(selection.isQuerySelection.value).toBe(isQuerySelection);
            expect(selection.selectionSize.value).toBe(totalItems);
        });

        it("breaks query selection and keeps remaining loaded items when an item is deselected", async () => {
            props.totalItemsInQuery.value = 100;
            await nextTick();
            selection.selectAllInCurrentQuery();
            await nextTick();
            expect(selection.isQuerySelection.value).toBe(true);
            expect(selection.selectionSize.value).toBe(100);
            expect(querySelectionBreak).not.toHaveBeenCalled();

            selection.setSelected(nth(props.allItems.value, 0), false);

            expect(selection.isQuerySelection.value).toBe(false);
            expect(selection.selectionSize.value).toBe(loadedItemCount - 1);
            expect(querySelectionBreak).toHaveBeenCalled();
        });

        it("breaks query selection and keeps loaded items when the query count changes", async () => {
            props.totalItemsInQuery.value = 100;
            await nextTick();
            selection.selectAllInCurrentQuery();
            await nextTick();
            expect(selection.isQuerySelection.value).toBe(true);
            expect(querySelectionBreak).not.toHaveBeenCalled();

            props.totalItemsInQuery.value = 80;
            await nextTick();

            expect(selection.isQuerySelection.value).toBe(false);
            expect(selection.selectionSize.value).toBe(loadedItemCount);
            expect(querySelectionBreak).toHaveBeenCalled();
        });
    });

    describe("selection size", () => {
        it("tracks individual selection and deselection by item key", () => {
            const firstItem = nth(props.allItems.value, 0);
            const secondItem = nth(props.allItems.value, 1);
            expect(selection.selectedItems.value.size).toBe(0);

            selection.setSelected(firstItem, true);
            expect(selection.selectedItems.value.size).toBe(1);

            selection.setSelected(secondItem, true);
            expect(selection.selectedItems.value.size).toBe(2);

            selection.setSelected(firstItem, false);
            expect(selection.selectedItems.value.size).toBe(1);
            expect(selection.selectedItems.value.has(getItemKey(firstItem))).toBe(false);
            expect(selection.selectedItems.value.has(getItemKey(secondItem))).toBe(true);
        });

        it("counts explicitly selected items outside query selection mode", () => {
            const items = createItems(3);
            selection.selectItems(items);
            expect(selection.isQuerySelection.value).toBe(false);
            expect(selection.selectionSize.value).toBe(3);

            selection.setSelected(nth(items, 0), false);

            expect(selection.selectionSize.value).toBe(2);
        });

        it("counts all items in the query even when no items are loaded", async () => {
            props.totalItemsInQuery.value = 100;
            await nextTick();
            props.allItems.value = [];

            selection.selectAllInCurrentQuery();
            await nextTick();

            expect(selection.isQuerySelection.value).toBe(true);
            expect(selection.selectionSize.value).toBe(100);
        });
    });

    function expectSelectionDisabled() {
        expect(selection.showSelection.value).toBe(false);
        expect(selection.selectionSize.value).toBe(0);
        expect(selection.selectedItems.value.size).toEqual(selection.selectionSize.value);
        expect(selection.isQuerySelection.value).toBe(false);
    }
});
