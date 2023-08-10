import { defineStore } from "pinia";

export const useHelpModeTextStore = defineStore("helpModeTextStore", {
    state: () => {
        return {
            helpmodetext: [],
        };
    },

    actions: {
        addHelpModeText(text) {
            //only push up to 20 items, then start removing the oldest items
            if (!this.helpmodetext.includes(text)) {
                if (this.helpmodetext.length < 20) {
                    this.helpmodetext.push(text);
                } else {
                    this.helpmodetext.shift();
                    this.helpmodetext.push(text);
                }
            }
        },
    },
});
