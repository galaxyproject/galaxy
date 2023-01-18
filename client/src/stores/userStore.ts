import { defineStore } from "pinia";

interface State {
    toggledSideBar: string;
}

export const useUserStore = defineStore("userStore", {
    state: (): State => ({
        toggledSideBar: "search",
    }),
    actions: {
        toggleSideBar(this: State, currentOpen: string) {
            this.toggledSideBar = this.toggledSideBar === currentOpen ? "" : currentOpen;
        },
    },
    persist: {
        paths: ["toggledSideBar"],
    },
});
