import { computed } from "vue";
import { useRoute } from "vue-router/composables";

export function usePanels() {
    const route = useRoute();

    const showPanels = computed(() => {
        const panels = route.query.hide_panels;
        if (panels !== undefined && panels !== null && typeof panels === "string") {
            return panels.toLowerCase() != "true";
        }
        return true;
    });

    return {
        showPanels,
    };
}
