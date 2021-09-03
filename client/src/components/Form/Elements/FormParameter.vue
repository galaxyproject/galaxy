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
    watch: {
        value() {
            if (this.parameter) {
                const currentValue = this.parameter.field.value();
                if (this.value !== currentValue) {
                    this.parameter.field.value(this.value);
                }
            }
        },
        attributes() {
            if (this.parameter) {
                if (this.parameter.field.update) {
                    this.parameter.field.update(this.attributes);
                    //this.parameter.field.trigger("change");
                }
            }
        },
    },
    created() {
        this.onRender();
    },
    methods: {
        onRender() {
            this.parameter = new ParameterFactory();
            this.$nextTick(() => {
                const el = this.$refs["parameter"];
                this.parameter.create({
                    ...this.attributes,
                    type: this.type,
                    value: this.value,
                    el,
                    onchange: () => {
                        this.$emit("input", this.parameter.field.value());
                    },
                });
            });
        },
    },
};
</script>
