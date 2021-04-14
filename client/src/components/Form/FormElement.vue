<template>
    <div :class="cls">
        <div v-if="hasError" class="ui-form-error">
            <span class="fa fa-arrow-down mr-1" />
            <span class="ui-form-error-text">{{ error }}</span>
        </div>
        <div class="ui-form-title">{{ title }}</div>
        <div class="ui-form-field">
            <FormInput :id="id" :value="value" :area="area" @onChange="onChange" />
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
        area: {
            type: Boolean,
            default: false,
        },
        error: {
            type: String,
            default: null,
        },
    },
    computed: {
        hasError() {
            return !!this.error;
        },
        cls() {
            if (this.hasError) {
                return "ui-form-element section-row alert alert-danger";
            } else {
                return "ui-form-element section-row";
            }
        },
    },
    methods: {
        onChange(value) {
            this.$emit("onChange", value);
        },
    },
};
</script>
