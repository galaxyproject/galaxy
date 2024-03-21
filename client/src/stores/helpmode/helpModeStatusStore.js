import { defineStore } from "pinia";

import { useHelpModeTextStore } from "./helpModeTextStore";

export const useHelpModeStatusStore = defineStore("helpModeStatusStore", {
    state: () => {
        return {
            helpmodestatus: false,
        };
    },

    actions: {
        setHelpModeStatus(status) {
            this.helpmodestatus = status;
            if (status == false) {
                useHelpModeTextStore().clearHelpModeText();
            }
        },
    },
});
