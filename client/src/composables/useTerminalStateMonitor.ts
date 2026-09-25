import { type ComputedRef, onScopeDispose, watch } from "vue";

import { useResourceWatcher } from "@/composables/resourceWatcher";
import { useHistoryStore } from "@/stores/historyStore";

type Poller = ReturnType<typeof useResourceWatcher>;

export function useTerminalStateMonitor(
    pendingHistoryIds: ComputedRef<string[]>,
    fetchForHistory: (historyId: string) => Promise<void>,
) {
    const historyStore = useHistoryStore();
    const pollers = new Map<string, Poller>();

    function stopPoller(historyId: string) {
        const poller = pollers.get(historyId);
        if (poller) {
            poller.dispose();
            pollers.delete(historyId);
        }
    }

    function ensureFallbackPoller(historyId: string) {
        if (pollers.has(historyId)) {
            return;
        }
        const watcher = useResourceWatcher(() => fetchForHistory(historyId));
        pollers.set(historyId, watcher);
        watcher.startWatchingResource();
    }

    function syncPollers() {
        const currentId = historyStore.currentHistoryId;
        const ids = new Set(pendingHistoryIds.value);

        for (const historyId of ids) {
            if (currentId && currentId !== historyId) {
                ensureFallbackPoller(historyId);
            }
        }

        for (const historyId of [...pollers.keys()]) {
            if (!ids.has(historyId) || (currentId && currentId === historyId)) {
                stopPoller(historyId);
            }
        }
    }

    watch(() => historyStore.currentHistoryId, syncPollers);

    onScopeDispose(() => {
        for (const historyId of [...pollers.keys()]) {
            stopPoller(historyId);
        }
    });

    return { syncPollers };
}
