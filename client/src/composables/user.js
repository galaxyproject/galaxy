import { computed, onMounted, inject } from "vue";

/**
 * composable user store wrapper
 * @returns currentUser computed
 */
export function useCurrentUser() {
    const store = inject("store");

    const currentUser = computed(() => store.getters["user/currentUser"]);

    onMounted(() => {
        store.dispatch("user/loadUser");
    });

    return { currentUser };
}
