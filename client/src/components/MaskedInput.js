import { BFormInput } from "bootstrap-vue/src/components/form-input";
import { createMask } from "imask";

export default {
    extends: BFormInput,
    props: {
        mask: {
            type: String,
            required: false,
            default: "",
        },
    },
    computed: {
        masker() {
            return createMask({
                mask: this.mask,
            });
        },
    },
    methods: {
        getFormatted(value) {
            const result = this.stringifyValue(value);
            if (this.mask.length) {
                return this.masker.resolve(result);
            }
            return result;
        },
    },
};
