/**
 * Stores Galaxy Help Mode's status
 */

import { defineStore } from "pinia";
import { ref } from "vue";

// import { useHelpModeTextStore } from "./helpModeTextStore";

export const useHelpModeStatusStore = defineStore("helpModeStatusStore", () => {
    // TODO: Maybe `status` should be tracked in local storage?
    // const status: Ref<boolean> = useUserLocalStorage("help-mode-status", false);

    const status = ref(false);
    const position = ref({ x: 0, y: 0 });

    // TODO: I removed the following since we now clear the text when we go away from
    // a component (the component is is destroyed) anyways.

    // Clear help mode text when help mode is disabled
    // watch(() => status.value, (newStatus) => {
    //     status.value = newStatus;
    //     if (!newStatus) {
    //         useHelpModeTextStore().clearHelpModeText();
    //     }
    // });

    return {
        status,
        position,
    };
});
