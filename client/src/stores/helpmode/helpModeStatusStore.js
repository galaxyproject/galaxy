import { defineStore } from "pinia";

export const useHelpModeStatusStore = defineStore("helpModeStatusStore", {
    state: () => {
        return {
            helpmodestatus: false,
        };
    },

    actions: {
        setHelpModeStatus(status) {
            this.helpmodestatus = status;
        },
    },
});
