import { computed, ref } from "vue";

import { useUserStore } from "@/stores/userStore";

export function useCurrentTheme() {
    const userStore = useUserStore();
    const currentTheme = computed(() => userStore.currentTheme);
    const settingTheme = ref(false);

    async function setCurrentTheme(theme: string) {
        settingTheme.value = true;
        await userStore.setCurrentTheme(theme);
        settingTheme.value = false;
    }
    return {
        currentTheme,
        setCurrentTheme,
        settingTheme,
    };
}
