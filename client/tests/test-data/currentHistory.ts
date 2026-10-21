import type { Decorator } from "@storybook/vue3-vite";
import { getActivePinia } from "pinia";
import { h, onBeforeUnmount } from "vue";

import type { AnyHistory } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";
import { seedCurrentHistory } from "@/stores/testUtils";

/**
 * Seeds the page's current history and restores its prior state when the story closes.
 * Supports a fresh store, or a reused store with a loaded selection or null selection.
 * A selected-but-unloaded history is unsupported: the selection is private, and reading
 * currentHistory can fetch it, so this helper cannot preserve that private selection.
 * Settle history requests before unmounting; a late response could overwrite restored state.
 */
export function withCurrentHistory(history: AnyHistory): Decorator {
    return (story) => ({
        setup() {
            const pinia = getActivePinia();
            if (!pinia) {
                throw new Error("Current history stories need Pinia");
            }
            const existed = pinia._s.has("historyStore");
            const previousState = pinia.state.value.historyStore;
            const store = useHistoryStore(pinia);
            const previousValues = { ...store.$state };
            const previousHistoryId = store.currentHistory?.id ?? null;
            // setHistory merges into the existing entry: detach both the map and its entries.
            store.storedHistories = Object.fromEntries(
                Object.entries(store.storedHistories).map(([id, entry]) => [id, { ...entry }]),
            );
            seedCurrentHistory({ ...history }, pinia);
            onBeforeUnmount(() => {
                Object.assign(store.$state, previousValues);
                // The backing selection permits null; the public setter's type only lists IDs.
                const restoreSelection = store.setCurrentHistoryId as (id: string | null) => void;
                restoreSelection(previousHistoryId);
                if (!existed) {
                    store.$dispose();
                    if (previousState === undefined) {
                        delete pinia.state.value[store.$id];
                    } else {
                        pinia.state.value[store.$id] = previousState;
                    }
                }
            });
            return () => h(story());
        },
    });
}
