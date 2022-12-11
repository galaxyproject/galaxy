import { prependPath } from "utils/redirect";

/* VueJS mixin with dataset downloadUrl */
export const downloadUrlMixin = {
    computed: {
        downloadUrl() {
            return prependPath(`api/datasets/${this.item.id}/display?to_ext=${this.item.extension}`);
        },
    },
};
