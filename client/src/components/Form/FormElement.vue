<template>
    <div :id="elementId" :class="['ui-form-element section-row', cls]" :tour_id="id">
        <div v-if="hasError" class="ui-form-error">
            <span class="fa fa-exclamation mr-1" />
            <span class="ui-form-error-text">{{ error }}</span>
        </div>
        <div class="ui-form-title">{{ title }}</div>
        <div class="ui-form-field">
            <FormParameter
                v-if="backbonejs"
                v-model="currentValue"
                :id="id"
                :type="type"
                :attributes="attrs"
                ref="params"
            />
            <FormBoolean v-else-if="type == 'boolean'" v-model="currentValue" :id="id" />
            <FormInput v-else="type == 'text'" v-model="currentValue" :id="id" :area="attrs['area']" />
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
        refreshOnChange: {
            type: Boolean,
            default: false,
        },
        help: {
            type: String,
            default: null,
        },
        error: {
            type: String,
            default: null,
        },
        backbonejs: {
            type: Boolean,
            default: false,
        },
        attributes: {
            type: Object,
            default: null,
        },
    },
    computed: {
        attrs() {
            return this.attributes || this.$attrs;
        },
        currentValue: {
            get() {
                return this.value;
            },
            set(val) {
                this.$emit("input", val);
                this.$emit("change", this.refreshOnChange);
            },
        },
        elementId() {
            return `form-element-${this.id}`;
        },
        hasError() {
            return !!this.error;
        },
        cls() {
            return this.hasError && "alert alert-info";
        },
    },
};
</script>
