<template>
    <div class="ui-form-element section-row">
        <div class="ui-form-title">{{ title }}</div>
        <div class="ui-form-field">
            <FormInput :id="id" :value="value" @onChange="onChange" />
            <span class="ui-form-info form-text text-muted mt-2">{{ help }}</span>
        </div>
    </div>
</template>
<script>
import FormInput from "./FormInput";

export default {
    components: {
        FormInput,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
        value: {
            type: String,
            default: "",
        },
        title: {
            type: String,
            default: "",
        },
        help: {
            type: String,
            default: "",
        },
    },
    data() {
        return { currentValue: value };
    },
    methods: {
        onChange(value) {
            this.$emit("onChange", value);
        },
    },
};
</script>
