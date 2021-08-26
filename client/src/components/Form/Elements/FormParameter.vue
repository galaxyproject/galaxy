<template>
    <div ref="parameter" />
</template>
<script>

import ParameterFactory from "mvc/form/form-parameters";

export default {
    props: {
        id: {
            type: String,
            required: true,
        },
        type: {
            type: String,
            required: true,
        },
        value: {
            default: null,
        },
        attributes: {
            type: Object,
            required: true,
        },
    },
    computed: {
        /*currentValue: {
            get() {
                return this.value;
            },
            set(val) {
                this.$emit("input", val);
            },
        },*/
    },
    created() {
        this.onRender();
    },
    methods: {
        onRender() {
            console.log(this.attributes);
            this.$nextTick(() => {
                const el = this.$refs["parameter"];
                this.parameter = new ParameterFactory({
                    ...this.attributes,
                    type: this.type,
                    value: this.value,
                    el,
                    onchange: (value) => {
                        this.$emit("input", val);
                    },
                });
            });
        },
    }
};
</script>
