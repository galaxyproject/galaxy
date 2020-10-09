<template>
    <div ref="inputs" />
</template>

<script>
import Form from "mvc/form/form-view";

export default {
    props: {
        inputs: {
            type: Array,
            required: true,
        },
    },
    mounted() {
        this.$nextTick(() => {
            const el = this.$refs["inputs"];
            this.form = new Form({
                el,
                inputs: this.inputs,
            }).on("change", this.onChange);
        });
    },
    methods: {
        onChange() {
            this.$emit("onChange", this.form.data.create());
        },
    },
};
</script>
