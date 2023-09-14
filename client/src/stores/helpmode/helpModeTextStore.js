import { defineStore } from "pinia";

export const useHelpModeTextStore = defineStore("helpModeText", {
    state: () => {
        return {
            helpmodetext: "Welcome to Galaxy Help Mode!",
        };
    },

    actions: {
        addHelpModeText(text) {
            this.helpmodetext = text;
        },
    },
});
