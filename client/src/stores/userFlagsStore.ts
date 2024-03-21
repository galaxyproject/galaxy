import { defineStore } from "pinia";

import { useUserLocalStorage } from "@/composables/userLocalStorage";

export type PreferredFormSelect = "none" | "multi" | "many";

export const useUserFlagsStore = defineStore("userFlagsStore", () => {
    const showSelectionQueryBreakWarning = useUserLocalStorage("user-flags-store-show-break-warning", true);
    const preferredFormSelectElement = useUserLocalStorage(
        "user-flags-store-preferred-form-select",
        "none" as PreferredFormSelect
    );

    function ignoreSelectionQueryBreakWarning() {
        showSelectionQueryBreakWarning.value = false;
    }

    return {
        showSelectionQueryBreakWarning,
        ignoreSelectionQueryBreakWarning,
        preferredFormSelectElement,
    };
});
