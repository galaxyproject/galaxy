import { defineStore } from "pinia";

import { useUserLocalStorage } from "@/composables/userLocalStorage";

export const useUserFlagsStore = defineStore("userFlagsStore", () => {
    const showSelectionQueryBreakWarning = useUserLocalStorage("user-flags-store-show-break-warning", true);

    function ignoreSelectionQueryBreakWarning() {
        showSelectionQueryBreakWarning.value = false;
    }

    return {
        showSelectionQueryBreakWarning,
        ignoreSelectionQueryBreakWarning,
    };
});
