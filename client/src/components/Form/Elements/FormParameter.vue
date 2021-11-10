<template>
    <div ref="parameter" />
</template>
<script>
import ParameterFactory from "./parameters";

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
            if (this.parameter && this.parameter.field) {
                const currentValue = this.parameter.field.value();
                if (JSON.stringify(this.value) !== JSON.stringify(currentValue)) {
                    this.parameter.field.value(this.value);
                }
            }
        },
        attributes() {
            if (this.parameter && this.parameter.field && this.parameter.field.update) {
                this.parameter.field.update(this.attributes);
                this.$emit("input", this.parameter.field.value());
            }
        },
    },
    mounted() {
        this.$nextTick(() => {
            this.parameter = new ParameterFactory();
            this.parameter.create({
                ...this.attributes,
                id: this.id,
                type: this.type,
                value: this.value,
                el: this.$refs["parameter"],
                onchange: () => {
                    if (this.parameter && this.parameter.field) {
                        this.$emit("input", this.parameter.field.value());
                    }
                },
            });
            this.$emit("input", this.parameter.field.value());
        });
    },
};
</script>
