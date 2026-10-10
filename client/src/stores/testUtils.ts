import { createPinia, type Pinia, setActivePinia } from "pinia";

import type { AnyHistory } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";

export function setupTestPinia() {
    setActivePinia(createPinia());
}

/**
 * Stores `history` and makes it the current history. `setCurrentHistoryId` alone is not
 * enough: `currentHistoryId` ignores an id that isn't stored and falls back to the first
 * stored history.
 */
export function seedCurrentHistory(history: AnyHistory, pinia?: Pinia) {
    const historyStore = useHistoryStore(pinia);
    historyStore.setHistory(history);
    historyStore.setCurrentHistoryId(history.id);
    return historyStore;
}
