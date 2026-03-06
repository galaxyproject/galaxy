import { computed, ref, unref, type ComputedRef, type Ref } from "vue";

export function useSidebarSelection<T>(items: Ref<T[]> | ComputedRef<T[]>, getId: (item: T) => string) {
    const selectionMode = ref(false);
    const selectedIds = ref(new Set<string>());
    const lastClickedIndex = ref<number | null>(null);

    const allSelected = computed(
        () => unref(items).length > 0 && selectedIds.value.size === unref(items).length
    );

    function toggleSelectionMode() {
        selectionMode.value = !selectionMode.value;
        if (!selectionMode.value) {
            selectedIds.value = new Set();
            lastClickedIndex.value = null;
        }
    }

    function toggleSelection(id: string) {
        const next = new Set(selectedIds.value);
        if (next.has(id)) {
            next.delete(id);
        } else {
            next.add(id);
        }
        selectedIds.value = next;
    }

    function toggleSelectAll() {
        if (allSelected.value) {
            selectedIds.value = new Set();
        } else {
            selectedIds.value = new Set(unref(items).map(getId));
        }
    }

    /** Handle a click in the context of selection mode.
     *  Returns true if the click was consumed (caller should not navigate). */
    function handleSelectionClick(item: T, index: number, event: MouseEvent): boolean {
        if (!selectionMode.value) {
            return false;
        }
        if (event.shiftKey && lastClickedIndex.value !== null) {
            const start = Math.min(lastClickedIndex.value, index);
            const end = Math.max(lastClickedIndex.value, index);
            const next = new Set(selectedIds.value);
            for (let i = start; i <= end; i++) {
                const el = unref(items)[i];
                if (el) {
                    const id = getId(el);
                    if (id) {
                        next.add(id);
                    }
                }
            }
            selectedIds.value = next;
        } else {
            toggleSelection(getId(item));
        }
        lastClickedIndex.value = index;
        return true;
    }

    /** Call after items are removed (e.g. batch delete). Prunes stale
     *  selections and exits selection mode if the list is now empty. */
    function pruneAfterDelete() {
        const currentIds = new Set(unref(items).map(getId));
        selectedIds.value = new Set([...selectedIds.value].filter((id) => currentIds.has(id)));
        if (unref(items).length === 0) {
            selectionMode.value = false;
        }
    }

    return {
        selectionMode,
        selectedIds,
        allSelected,
        toggleSelectionMode,
        toggleSelection,
        toggleSelectAll,
        handleSelectionClick,
        pruneAfterDelete,
    };
}
