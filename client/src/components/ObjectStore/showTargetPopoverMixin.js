import ShowSelectedObjectStore from "./ShowSelectedObjectStore";
import { localize } from "utils/localization";

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
        title() {
            return localize(`Preferred Target Object Store ${this.titleSuffix || ""}`);
        },
    },
};
