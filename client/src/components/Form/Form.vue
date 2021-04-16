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
                }).on("change", this.onChange);
                this.onChange();
            });
        },
    },
};
</script>
