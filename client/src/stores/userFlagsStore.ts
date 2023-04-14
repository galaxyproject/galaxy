import { ref } from "vue";
import { defineStore } from "pinia";

export const useUserFlagsStore = defineStore("userFlagsStore", () => {
    const showSelectionQueryBreakWarning = ref(true);

    function ignoreSelectionQueryBreakWarning() {
        showSelectionQueryBreakWarning.value = false;
    }

    return {
        showSelectionQueryBreakWarning,
        ignoreSelectionQueryBreakWarning,
    };
});
