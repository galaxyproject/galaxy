import { computed } from "vue";
import { useRoute } from "vue-router/composables";

import { useUserStore } from "@/stores/userStore";

export function usePanels() {
    const userStore = useUserStore();
    const route = useRoute();

    const showPanels = computed(() => {
        const panels = route.query.hide_panels;
        if (panels !== undefined && panels !== null && typeof panels === "string") {
            return panels.toLowerCase() != "true";
        }
        return true;
    });

    const showActivityBar = computed(() => showPanels.value && userStore.showActivityBar && !userStore.isAnonymous);
    const showToolbox = computed(() => showPanels.value && !showActivityBar.value);

    return {
        showPanels,
        showActivityBar,
        showToolbox,
    };
}
