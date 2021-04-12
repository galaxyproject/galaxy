<template>
    <Form inputs="inputs" />
</template>

<script>
import Form from "mvc/form/form-view";

export default {
    props: {
        getNode: () => {},
    },
    mounted() {
        this.$nextTick(() => {
            const el = this.$refs["inputs"];
            this.form = new Form({
                el,
                inputs: this.inputs,
            }).on("change", this.onChange);
            this.onChange();
        });
    },
    methods: {
        onChange() {
            this.$emit("onChange", this.form.data.create());
        },
    },
};
</script>
