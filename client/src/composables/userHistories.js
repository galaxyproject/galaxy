import { computed, watch, unref, inject } from "vue";

export function useUserHistories(user) {
    const store = inject("store");

    watch(
        () => unref(user),
        (newUser, oldUser) => {
            if (newUser?.id !== oldUser?.id) {
                store.dispatch("history/loadHistories");
            }
        },
        { immediate: true }
    );

    const currentHistoryId = computed(() => store.getters["history/currentHistoryId"]);

    return { currentHistoryId };
}
