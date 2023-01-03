import { computed } from "vue";
import store from "store";

export function useCurrentTheme() {
    const currentTheme = computed(() => store.getters["userFlags/getCurrentTheme"]);

    function setCurrentTheme(theme) {
        store.commit("userFlags/setCurrentTheme", theme);
    }

    return {
        currentTheme,
        setCurrentTheme,
    };
}
