import BInput from "bootstrap-vue/es/components/form-input/form-input";
import { createMask } from "imask";

export default {
    extends: BInput,
    props: {
        mask: {
            type: String,
            required: false,
            default: ""
        }
    },
    computed: {
        masker() {
            return createMask({
                mask: this.mask
            });
        }
    },
    methods: {
        getFormatted(value) {
            const result = this.stringifyValue(value);
            if (this.mask.length) {
                return this.masker.resolve(result);
            }
            return result;
        }
    }
};
