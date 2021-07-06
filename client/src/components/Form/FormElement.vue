<template>
    <div :class="cls" :tour_id="id">
        <div v-if="hasError" class="ui-form-error">
            <span class="fa fa-arrow-down mr-1" />
            <span class="ui-form-error-text">{{ error }}</span>
        </div>
        <div class="ui-form-title">{{ title }}</div>
        <div class="ui-form-field">
            <FormInput v-if="type == 'text'" :id="id" :area="area" v-model="currentValue" />
            <FormBoolean v-else-if="type == 'boolean'" :id="id" v-model="currentValue" />
            <span class="ui-form-info form-text text-muted mt-2">{{ help }}</span>
        </div>
    </div>
</template>
<script>
import FormBoolean from "./Elements/FormBoolean";
import FormInput from "./Elements/FormInput";

export default {
    components: {
        FormBoolean,
        FormInput,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
        value: {
            type: [String, Boolean],
            default: null,
        },
        title: {
            type: String,
            default: null,
        },
        help: {
            type: String,
            default: null,
        },
        area: {
            type: Boolean,
            default: false,
        },
        error: {
            type: String,
            default: null,
        },
        type: {
            type: String,
            default: "text",
        },
    },
    computed: {
        currentValue: {
            get() {
                return this.value;
            },
            set(val) {
                this.$emit("input", val);
            },
        },
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
};
</script>
