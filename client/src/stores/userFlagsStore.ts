import { defineStore } from "pinia";

import { useUserLocalStorage } from "@/composables/userLocalStorage";

export type PreferredFormSelect = "none" | "multi" | "many";

export const useUserFlagsStore = defineStore("userFlagsStore", () => {
    const showSelectionQueryBreakWarning = useUserLocalStorage("user-flags-store-show-break-warning", true);
    const preferredFormSelectElement = useUserLocalStorage(
        "user-flags-store-preferred-form-select",
        "none" as PreferredFormSelect,
    );
    const showStorageOperationsHelperPopover = useUserLocalStorage(
        "user-flags-store-show-storage-operations-helper-popover",
        true,
    );

    function ignoreSelectionQueryBreakWarning() {
        showSelectionQueryBreakWarning.value = false;
    }

    function ignoreStorageOperationsHelperPopover() {
        showStorageOperationsHelperPopover.value = false;
    }

    return {
        showSelectionQueryBreakWarning,
        ignoreSelectionQueryBreakWarning,
        preferredFormSelectElement,
        showStorageOperationsHelperPopover,
        ignoreStorageOperationsHelperPopover,
    };
});
