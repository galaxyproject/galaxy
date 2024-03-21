import { defineStore } from "pinia";

import config from "./helpTextConfig.yml";

export const useHelpModeTextStore = defineStore("helpModeText", {
    state: () => {
        return {
            helpmodetext: "Welcome to Galaxy Help Mode!",
        };
    },

    actions: {
        addHelpModeText(text) {
            const file_path = config[text];
            fetch("https://raw.githubusercontent.com/assuntad23/galaxy-help-markdown/main/" + file_path)
                .then((response) => response.text())
                .then((text) => {
                    this.helpmodetext = text;
                });
        },
        clearHelpModeText() {
            this.helpmodetext = "Welcome to Galaxy Help Mode!";
        },
    },
});
