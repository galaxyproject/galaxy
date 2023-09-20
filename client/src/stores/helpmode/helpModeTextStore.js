import { defineStore } from "pinia";

import config from './helpTextConfig.yml';

export const useHelpModeTextStore = defineStore("helpModeText", {
    state: () => {
        return {
            helpmodetext: "Welcome to Galaxy Help Mode!",
        };
    },

    actions: {
        addHelpModeText(text) {
            this.helpmodetext = config[text];
        },
    },
});
