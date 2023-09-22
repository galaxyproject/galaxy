<template>
    <b-form-input v-model="localValue" class="directory-form-input" :placeholder="placeholder" @click="selectFile">
    </b-form-input>
</template>

<script>
import { BFormInput } from "bootstrap-vue";
import { filesDialog } from "utils/data";

export default {
    components: { BFormInput },
    props: {
        value: {
            type: String,
        },
        mode: {
            type: String,
            default: "file",
        },
        requireWritable: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            localValue: this.value,
        };
    },
    computed: {
        placeholder() {
            return `Click to select ${this.mode}`;
        },
    },
    watch: {
        localValue(newValue) {
            this.$emit("input", newValue);
        },
        value(newValue) {
            this.localValue = newValue;
        },
    },
    methods: {
        selectFile() {
            const props = {
                mode: this.mode,
                requireWritable: this.requireWritable,
            };
            filesDialog((selected) => {
                this.localValue = selected?.url;
            }, props);
        },
    },
};
</script>
