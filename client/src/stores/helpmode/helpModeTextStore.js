import { defineStore } from "pinia";

export const useHelpModeTextStore = defineStore("helpModeTextStore", {
    state: () => {
        return {
            helpmodetext: "",
        };
    },

    actions: {
        addHelpModeText(text) {
            //only push up to 20 items, then start removing the oldest items
            //do we need to keep track of more than one item? or is this an enhancement?
            // if (!this.helpmodetext.includes(text)) {
            //     if (this.helpmodetext.length < 20) {
            //         this.helpmodetext.push(text);
            //     } else {
            //         this.helpmodetext.shift();
            //         this.helpmodetext.push(text);
            //     }
            // }
            this.helpmodetext = text;
        },
    },
});
