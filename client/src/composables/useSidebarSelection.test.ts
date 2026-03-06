import { ref } from "vue";
import { describe, expect, it } from "vitest";

import { useSidebarSelection } from "./useSidebarSelection";

interface TestItem {
    id: string;
    name: string;
}

function makeItems(...ids: string[]): TestItem[] {
    return ids.map((id) => ({ id, name: `Item ${id}` }));
}

function mouseEvent(opts: Partial<MouseEvent> = {}): MouseEvent {
    return { shiftKey: false, ...opts } as MouseEvent;
}

describe("useSidebarSelection", () => {
    it("starts in non-selection mode with empty selection", () => {
        const items = ref(makeItems("a", "b", "c"));
        const { selectionMode, selectedIds, allSelected } = useSidebarSelection(items, (i) => i.id);

        expect(selectionMode.value).toBe(false);
        expect(selectedIds.value.size).toBe(0);
        expect(allSelected.value).toBe(false);
    });

    describe("toggleSelectionMode", () => {
        it("toggles selection mode on", () => {
            const items = ref(makeItems("a", "b"));
            const { selectionMode, toggleSelectionMode } = useSidebarSelection(items, (i) => i.id);

            toggleSelectionMode();
            expect(selectionMode.value).toBe(true);
        });

        it("clears selections when toggling off", () => {
            const items = ref(makeItems("a", "b"));
            const { selectionMode, selectedIds, toggleSelectionMode, toggleSelection } = useSidebarSelection(
                items,
                (i) => i.id
            );

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
            const items = ref(makeItems("a", "b"));
            const { selectedIds, toggleSelection } = useSidebarSelection(items, (i) => i.id);

            toggleSelection("a");
            expect(selectedIds.value.has("a")).toBe(true);

            toggleSelection("a");
            expect(selectedIds.value.has("a")).toBe(false);
        });

        it("can select multiple ids", () => {
            const items = ref(makeItems("a", "b", "c"));
            const { selectedIds, toggleSelection } = useSidebarSelection(items, (i) => i.id);

            toggleSelection("a");
            toggleSelection("c");
            expect(selectedIds.value.size).toBe(2);
            expect(selectedIds.value.has("a")).toBe(true);
            expect(selectedIds.value.has("c")).toBe(true);
        });
    });

    describe("toggleSelectAll", () => {
        it("selects all items", () => {
            const items = ref(makeItems("a", "b", "c"));
            const { selectedIds, allSelected, toggleSelectAll } = useSidebarSelection(items, (i) => i.id);

            toggleSelectAll();
            expect(selectedIds.value.size).toBe(3);
            expect(allSelected.value).toBe(true);
        });

        it("deselects all when all are selected", () => {
            const items = ref(makeItems("a", "b"));
            const { selectedIds, allSelected, toggleSelectAll } = useSidebarSelection(items, (i) => i.id);

            toggleSelectAll();
            expect(allSelected.value).toBe(true);

            toggleSelectAll();
            expect(selectedIds.value.size).toBe(0);
            expect(allSelected.value).toBe(false);
        });
    });

    describe("allSelected", () => {
        it("is false for empty items list", () => {
            const items = ref<TestItem[]>([]);
            const { allSelected } = useSidebarSelection(items, (i) => i.id);
            expect(allSelected.value).toBe(false);
        });

        it("reacts to items changes", () => {
            const items = ref(makeItems("a", "b"));
            const { allSelected, toggleSelectAll } = useSidebarSelection(items, (i) => i.id);

            toggleSelectAll();
            expect(allSelected.value).toBe(true);

            items.value = makeItems("a", "b", "c");
            expect(allSelected.value).toBe(false);
        });
    });

    describe("handleSelectionClick", () => {
        it("returns false and does not mutate state when not in selection mode", () => {
            const items = ref(makeItems("a", "b"));
            const { selectedIds, handleSelectionClick } = useSidebarSelection(items, (i) => i.id);

            const consumed = handleSelectionClick(items.value[0]!, 0, mouseEvent());
            expect(consumed).toBe(false);
            expect(selectedIds.value.size).toBe(0);
        });

        it("toggles item and returns true in selection mode", () => {
            const items = ref(makeItems("a", "b"));
            const { selectedIds, toggleSelectionMode, handleSelectionClick } = useSidebarSelection(
                items,
                (i) => i.id
            );

            toggleSelectionMode();
            const consumed = handleSelectionClick(items.value[0]!, 0, mouseEvent());
            expect(consumed).toBe(true);
            expect(selectedIds.value.has("a")).toBe(true);

            handleSelectionClick(items.value[0]!, 0, mouseEvent());
            expect(selectedIds.value.has("a")).toBe(false);
        });

        it("shift-click selects range", () => {
            const items = ref(makeItems("a", "b", "c", "d", "e"));
            const { selectedIds, toggleSelectionMode, handleSelectionClick } = useSidebarSelection(
                items,
                (i) => i.id
            );

            toggleSelectionMode();
            handleSelectionClick(items.value[1]!, 1, mouseEvent());
            handleSelectionClick(items.value[3]!, 3, mouseEvent({ shiftKey: true }));

            expect(selectedIds.value.size).toBe(3);
            expect(selectedIds.value.has("b")).toBe(true);
            expect(selectedIds.value.has("c")).toBe(true);
            expect(selectedIds.value.has("d")).toBe(true);
        });

        it("shift-click backwards selects range", () => {
            const items = ref(makeItems("a", "b", "c", "d"));
            const { selectedIds, toggleSelectionMode, handleSelectionClick } = useSidebarSelection(
                items,
                (i) => i.id
            );

            toggleSelectionMode();
            handleSelectionClick(items.value[3]!, 3, mouseEvent());
            handleSelectionClick(items.value[0]!, 0, mouseEvent({ shiftKey: true }));

            expect(selectedIds.value.size).toBe(4);
        });

        it("shift-click without prior click acts as normal click", () => {
            const items = ref(makeItems("a", "b"));
            const { selectedIds, toggleSelectionMode, handleSelectionClick } = useSidebarSelection(
                items,
                (i) => i.id
            );

            toggleSelectionMode();
            handleSelectionClick(items.value[1]!, 1, mouseEvent({ shiftKey: true }));
            expect(selectedIds.value.size).toBe(1);
            expect(selectedIds.value.has("b")).toBe(true);
        });

        it("resets shift-click anchor when toggling mode off and back on", () => {
            const items = ref(makeItems("a", "b", "c", "d"));
            const { selectedIds, toggleSelectionMode, handleSelectionClick } = useSidebarSelection(
                items,
                (i) => i.id
            );

            toggleSelectionMode();
            handleSelectionClick(items.value[0]!, 0, mouseEvent());
            toggleSelectionMode();
            toggleSelectionMode();
            handleSelectionClick(items.value[3]!, 3, mouseEvent({ shiftKey: true }));
            expect(selectedIds.value.size).toBe(1);
            expect(selectedIds.value.has("d")).toBe(true);
        });
    });

    describe("pruneAfterDelete", () => {
        it("removes stale IDs after items are removed", () => {
            const items = ref(makeItems("a", "b", "c"));
            const { selectedIds, toggleSelection, pruneAfterDelete } = useSidebarSelection(items, (i) => i.id);

            toggleSelection("a");
            toggleSelection("b");
            toggleSelection("c");

            items.value = makeItems("b");
            pruneAfterDelete();

            expect(selectedIds.value.size).toBe(1);
            expect(selectedIds.value.has("b")).toBe(true);
        });

        it("exits selection mode when list is empty", () => {
            const items = ref(makeItems("a"));
            const { selectionMode, toggleSelectionMode, toggleSelection, pruneAfterDelete } = useSidebarSelection(
                items,
                (i) => i.id
            );

            toggleSelectionMode();
            toggleSelection("a");

            items.value = [];
            pruneAfterDelete();

            expect(selectionMode.value).toBe(false);
        });

        it("stays in selection mode when items remain", () => {
            const items = ref(makeItems("a", "b"));
            const { selectionMode, toggleSelectionMode, toggleSelection, pruneAfterDelete } = useSidebarSelection(
                items,
                (i) => i.id
            );

            toggleSelectionMode();
            toggleSelection("a");

            items.value = makeItems("b");
            pruneAfterDelete();

            expect(selectionMode.value).toBe(true);
        });
    });
});
