import { beforeEach, describe, expect, it } from "vitest";
import { ref } from "vue";

import { setupTestPinia } from "@/stores/testUtils";

import { useSidebarSelection } from "./useSidebarSelection";

interface TestItem {
    id: string;
    name: string;
}

function makeItems(...ids: string[]): TestItem[] {
    return ids.map((id) => ({ id, name: `Item ${id}` }));
}

function createSelection(...ids: string[]) {
    const items = ref(makeItems(...ids));
    return { items, ...useSidebarSelection(items, (item) => item.id) };
}

describe("useSidebarSelection", () => {
    beforeEach(() => {
        setupTestPinia();
    });

    it("starts in non-selection mode with empty selection", () => {
        const { selectionMode, selectedIds, allSelected } = createSelection("a", "b", "c");

        expect(selectionMode.value).toBe(false);
        expect(selectedIds.value.size).toBe(0);
        expect(allSelected.value).toBe(false);
    });

    describe("toggleSelectionMode", () => {
        it("toggles selection mode on", () => {
            const { selectionMode, toggleSelectionMode } = createSelection("a", "b");

            toggleSelectionMode();
            expect(selectionMode.value).toBe(true);
        });

        it("clears selections when toggling off", () => {
            const { selectionMode, selectedIds, toggleSelectionMode, toggleSelection } = createSelection("a", "b");

            toggleSelectionMode();
            toggleSelection("a");
            expect(selectedIds.value.has("a")).toBe(true);

            toggleSelectionMode();
            expect(selectionMode.value).toBe(false);
            expect(selectedIds.value.size).toBe(0);
        });
    });

    describe("toggleSelection", () => {
        it("adds then removes an id", () => {
            const { selectedIds, toggleSelection } = createSelection("a", "b");

            toggleSelection("a");
            expect(selectedIds.value.has("a")).toBe(true);

            toggleSelection("a");
            expect(selectedIds.value.has("a")).toBe(false);
        });

        it("can select multiple ids", () => {
            const { selectedIds, toggleSelection } = createSelection("a", "b", "c");

            toggleSelection("a");
            toggleSelection("c");
            expect(selectedIds.value.size).toBe(2);
            expect(selectedIds.value.has("a")).toBe(true);
            expect(selectedIds.value.has("c")).toBe(true);
        });
    });

    describe("toggleSelectAll", () => {
        it("selects all items", () => {
            const { selectedIds, allSelected, toggleSelectAll } = createSelection("a", "b", "c");

            toggleSelectAll();
            expect(selectedIds.value.size).toBe(3);
            expect(allSelected.value).toBe(true);
        });

        it("deselects all when all are selected", () => {
            const { selectedIds, allSelected, toggleSelectAll } = createSelection("a", "b");

            toggleSelectAll();
            expect(allSelected.value).toBe(true);

            toggleSelectAll();
            expect(selectedIds.value.size).toBe(0);
            expect(allSelected.value).toBe(false);
        });
    });

    describe("allSelected", () => {
        it("is false for empty items list", () => {
            const { allSelected } = createSelection();
            expect(allSelected.value).toBe(false);
        });

        it("reacts to items changes", () => {
            const { items, allSelected, toggleSelectAll } = createSelection("a", "b");

            toggleSelectAll();
            expect(allSelected.value).toBe(true);

            items.value = makeItems("a", "b", "c");
            expect(allSelected.value).toBe(false);
        });
    });

    describe("handleSelectionClick", () => {
        it("returns false and does not mutate state when not in selection mode", () => {
            const { items, selectedIds, handleSelectionClick } = createSelection("a", "b");

            const consumed = handleSelectionClick(items.value[0]!, 0, new MouseEvent("click"));
            expect(consumed).toBe(false);
            expect(selectedIds.value.size).toBe(0);
        });

        it("toggles item and returns true in selection mode", () => {
            const { items, selectedIds, toggleSelectionMode, handleSelectionClick } = createSelection("a", "b");

            toggleSelectionMode();
            const consumed = handleSelectionClick(items.value[0]!, 0, new MouseEvent("click"));
            expect(consumed).toBe(true);
            expect(selectedIds.value.has("a")).toBe(true);

            handleSelectionClick(items.value[0]!, 0, new MouseEvent("click"));
            expect(selectedIds.value.has("a")).toBe(false);
        });

        it("shift-click selects range", () => {
            const { items, selectedIds, toggleSelectionMode, handleSelectionClick } = createSelection(
                "a",
                "b",
                "c",
                "d",
                "e",
            );

            toggleSelectionMode();
            handleSelectionClick(items.value[1]!, 1, new MouseEvent("click"));
            handleSelectionClick(items.value[3]!, 3, new MouseEvent("click", { shiftKey: true }));

            expect(selectedIds.value.size).toBe(3);
            expect(selectedIds.value.has("b")).toBe(true);
            expect(selectedIds.value.has("c")).toBe(true);
            expect(selectedIds.value.has("d")).toBe(true);
        });

        it("shift-click backwards selects range", () => {
            const { items, selectedIds, toggleSelectionMode, handleSelectionClick } = createSelection(
                "a",
                "b",
                "c",
                "d",
            );

            toggleSelectionMode();
            handleSelectionClick(items.value[3]!, 3, new MouseEvent("click"));
            handleSelectionClick(items.value[0]!, 0, new MouseEvent("click", { shiftKey: true }));

            expect(selectedIds.value.size).toBe(4);
        });

        it("shift-click without prior click acts as normal click", () => {
            const { items, selectedIds, toggleSelectionMode, handleSelectionClick } = createSelection("a", "b");

            toggleSelectionMode();
            handleSelectionClick(items.value[1]!, 1, new MouseEvent("click", { shiftKey: true }));
            expect(selectedIds.value.size).toBe(1);
            expect(selectedIds.value.has("b")).toBe(true);
        });

        it("resets shift-click anchor when toggling mode off and back on", () => {
            const { items, selectedIds, toggleSelectionMode, handleSelectionClick } = createSelection(
                "a",
                "b",
                "c",
                "d",
            );

            toggleSelectionMode();
            handleSelectionClick(items.value[0]!, 0, new MouseEvent("click"));
            toggleSelectionMode();
            toggleSelectionMode();
            handleSelectionClick(items.value[3]!, 3, new MouseEvent("click", { shiftKey: true }));
            expect(selectedIds.value.size).toBe(1);
            expect(selectedIds.value.has("d")).toBe(true);
        });
    });

    describe("pruneAfterDelete", () => {
        it("removes stale IDs after items are removed", () => {
            const { items, selectedIds, toggleSelection, pruneAfterDelete } = createSelection("a", "b", "c");

            toggleSelection("a");
            toggleSelection("b");
            toggleSelection("c");

            items.value = makeItems("b");
            pruneAfterDelete();

            expect(selectedIds.value.size).toBe(1);
            expect(selectedIds.value.has("b")).toBe(true);
        });

        it("exits selection mode when list is empty", () => {
            const { items, selectionMode, toggleSelectionMode, toggleSelection, pruneAfterDelete } =
                createSelection("a");

            toggleSelectionMode();
            toggleSelection("a");

            items.value = [];
            pruneAfterDelete();

            expect(selectionMode.value).toBe(false);
        });

        it("stays in selection mode when items remain", () => {
            const { items, selectionMode, toggleSelectionMode, toggleSelection, pruneAfterDelete } = createSelection(
                "a",
                "b",
            );

            toggleSelectionMode();
            toggleSelection("a");

            items.value = makeItems("b");
            pruneAfterDelete();

            expect(selectionMode.value).toBe(true);
        });
    });
});
