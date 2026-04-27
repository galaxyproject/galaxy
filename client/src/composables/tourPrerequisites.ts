import type { Prerequisite } from "@/api/tours";
import { useActivityStore } from "@/stores/activityStore";

import { useGlobalUploadModal } from "./globalUploadModal";

/**
 * Prerequisites for tour steps. If any step has an element that requires a prerequisite to be opened
 * (e.g. an upload dialog), then the prerequisite can be added here to ensure that the tour step will work correctly.
 */
export function useTourPrerequisites() {
    const { openGlobalUploadModal } = useGlobalUploadModal();

    const activityStore = useActivityStore("default");

    const tourPrerequisites: Record<Prerequisite, () => void> = {
        ensure_history_panel_open: () => {
            const panel = document.querySelector("#current-history-panel");
            if (!panel) {
                const historyButton = document.querySelector('[data-description="history panel expand button"]');
                if (historyButton) {
                    (historyButton as HTMLElement).click();
                }
            }
        },
        ensure_tool_panel_open: () => {
            if (activityStore.toggledSideBar !== "tools") {
                activityStore.toggleSideBar("tools");
            }
        },
        ensure_upload_open: openGlobalUploadModal,
    };

    return {
        tourPrerequisites,
    };
}
