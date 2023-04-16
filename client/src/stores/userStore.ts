import { defineStore } from "pinia";

interface State {
    toggledActivityBar: boolean;
    toggledSideBar: string;
}

export const useUserStore = defineStore("userStore", {
    state: (): State => ({
        toggledActivityBar: false,
        toggledSideBar: "search",
    }),
    actions: {
        toggleActivityBar(this: State) {
            this.toggledActivityBar = !this.toggledActivityBar;
        },
        toggleSideBar(this: State, currentOpen: string) {
            this.toggledSideBar = this.toggledSideBar === currentOpen ? "" : currentOpen;
        },
    },
    persist: {
        paths: ["toggledActivityBar", "toggledSideBar"],
    },
});
