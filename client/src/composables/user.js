import { computed, onMounted } from "vue";
import store from "store";

/**
 * composable user store wrapper
 * @returns currentUser computed
 */
export function useCurrentUser() {
    const user = computed(() => store.getters["user/currentUser"]);

    onMounted(() => {
        store.dispatch("user/loadUser");
    });

    return user;
}
