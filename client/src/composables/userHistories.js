import { useHistoryStore } from "stores/historyStore";
import { computed, unref, watch } from "vue";

export function useUserHistories(user) {
    const historyStore = useHistoryStore();

    watch(
        () => unref(user),
        async (newUser, oldUser) => {
            if (newUser?.id !== oldUser?.id) {
                await historyStore.loadHistories();
            }
        },
        { immediate: true }
    );

    const currentHistoryId = computed(() => historyStore.currentHistoryId);
    const currentHistory = computed(() => historyStore.currentHistory);

    return {
        currentHistoryId,
        currentHistory,
    };
}
