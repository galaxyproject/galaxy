import { onMounted, ref } from "vue";

import { type HistorySummaryExtended } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";

export function useDetailedHistory(historyId: string) {
    const historyStore = useHistoryStore();

    onMounted(async () => {
        detailedHistory.value = await historyStore.loadHistoryById(historyId);
    });

    const detailedHistory = ref<HistorySummaryExtended>();

    return {
        detailedHistory,
    };
}
