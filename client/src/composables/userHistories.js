import { computed, watch, unref } from "vue";
import { useHistoryStore } from "stores/historyStore";

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

    return { currentHistoryId };
}
