import { ref } from "vue";
import { defineStore } from "pinia";

export const useHistoryStore = defineStore(
    "historyStore",
    () => {
        const pinnedHistories = ref([]);

        const pinHistory = (historyId) => {
            pinnedHistories.value.push({ id: historyId });
        };

        const unpinHistory = (historyId) => {
            pinnedHistories.value = pinnedHistories.value.filter((h) => h.id !== historyId);
        };

        return {
            pinnedHistories,
            pinHistory,
            unpinHistory,
        };
    },
    {
        persist: ["pinnedHistories"],
    }
);
