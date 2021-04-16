<template>
    <div ref="inputs" />
</template>

<script>
import Form from "mvc/form/form-view";

export default {
    props: {
        id: {
            type: String,
            required: true,
        },
        inputs: {
            type: Array,
            required: true,
        },
        textEnable: {
            type: String,
            default: null,
        },
        textDisable: {
            type: String,
            default: null,
        },
        initialErrors: {
            type: Boolean,
            default: false,
        },
    },
    watch: {
        id() {
            this.onRender();
        },
    },
    mounted() {
        this.onRender();
    },
    methods: {
        onChange() {
            this.$emit("onChange", this.form.data.create());
        },
        onRender() {
            this.$nextTick(() => {
                const el = this.$refs["inputs"];
                this.form = new Form({
                    el,
                    inputs: this.inputs,
                    initial_errors: this.initialErrors,
                    text_enable: this.textEnable,
                    text_disable: this.textDisable,
                }).on("change", this.onChange);
                this.onChange();
            });
        },
    },
};
</script>
