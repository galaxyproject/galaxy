import { mapState } from "pinia";

import { useConfigStore } from "@/stores/configurationStore";

import ShowSelectedObjectStore from "./ShowSelectedObjectStore";

export default {
    components: {
        ShowSelectedObjectStore,
    },
    props: {
        titleSuffix: {
            type: String,
            default: null,
        },
    },
    computed: {
        ...mapState(useConfigStore, ["config"]),
        preferredOrEmptyString() {
            if (this.config?.object_store_always_respect_user_selection) {
                return "";
            } else {
                return "首选";
            }
        },
        title() {
            return this.l(`${this.preferredOrEmptyString} 目标存储位置 ${this.titleSuffix || ""}`);
        },
    },
};
