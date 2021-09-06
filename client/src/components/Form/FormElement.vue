<template>
    <div :class="cls" :tour_id="id">
        <div v-if="hasError" class="ui-form-error">
            <span class="fa fa-arrow-down mr-1" />
            <span class="ui-form-error-text">{{ error }}</span>
        </div>
        <div class="ui-form-title">{{ title }}</div>
        <div class="ui-form-field">
            <FormBoolean v-if="type == 'boolean1'" :id="id" v-model="currentValue" />
            <FormInput v-else-if="type == 'text1'" :id="id" :area="$attrs['area']" v-model="currentValue" />
            <FormParameter v-else v-model="currentValue" :id="id" :type="type" :attributes="$attrs" />
            <span class="ui-form-info form-text text-muted mt-2">{{ help }}</span>
        </div>
    </div>
</template>
<script>
import FormBoolean from "./Elements/FormBoolean";
import FormInput from "./Elements/FormInput";
import FormParameter from "./Elements/FormParameter";

export default {
    components: {
        FormBoolean,
        FormInput,
        FormParameter,
    },
    props: {
        id: {
            type: String,
            required: false,
        },
        type: {
            type: String,
            default: "text",
        },
        value: {
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
        error: {
            type: String,
            default: null,
        },
    },
    created() {
        this.$emit("input", this.value, this.id, false);
    },
    computed: {
        currentValue: {
            get() {
                return this.value;
            },
            set(val) {
                this.$emit("input", val, this.id, true);
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
