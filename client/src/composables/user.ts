import { computed } from "vue";

import { useUserStore } from "@/stores/userStore";

export function useCurrentTheme() {
    const userStore = useUserStore();
    const currentTheme = computed(() => userStore.currentTheme);
    function setCurrentTheme(theme: string) {
        userStore.setCurrentTheme(theme);
    }
    return {
        currentTheme,
        setCurrentTheme,
    };
}
