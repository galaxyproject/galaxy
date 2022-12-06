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

    const addFavoriteTool = async (toolId) => await store.dispatch("user/addFavoriteTool", toolId);
    const removeFavoriteTool = async (toolId) => await store.dispatch("user/removeFavoriteTool", toolId);

    return { currentUser, addFavoriteTool, removeFavoriteTool };
}
