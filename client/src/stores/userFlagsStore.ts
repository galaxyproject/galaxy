import { defineStore } from "pinia";
import { ref } from "vue";

export const useUserFlagsStore = defineStore(
    "userFlagsStore",
    () => {
        const showSelectionQueryBreakWarning = ref(true);

        function ignoreSelectionQueryBreakWarning() {
            showSelectionQueryBreakWarning.value = false;
        }

        return {
            showSelectionQueryBreakWarning,
            ignoreSelectionQueryBreakWarning,
        };
    },
    {
        persist: true,
    }
);
