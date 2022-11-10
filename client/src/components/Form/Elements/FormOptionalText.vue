<template>
    <div>
        <b-form-checkbox v-model="status" value="optional_text" unchecked-value="no_optional_text" switch
            >Set value for this optinonal select field?</b-form-checkbox
        >
        <FormText
            v-if="status == 'optional_text'"
            :id="id"
            v-model="currentValue"
            :readonly="readonly"
            :value="value"
            :area="area"
            :placeholder="placeholder"
            :color="color"
            :multiple="multiple"
            :style="tyle"
            :datalist="datalist"
            :type="type" />
    </div>
</template>

<script>
import FormText from "./FormText";
export default {
    components: {
        FormText,
    },
    props: {
        value: {
            required: false,
            default: "",
        },
        id: {
            type: String,
            required: false,
        },
        type: {
            type: String,
            required: false,
            default: "text",
        },
        area: {
            // <textarea> instead of <input> element
            type: Boolean,
            required: false,
            default: false,
        },
        multiple: {
            // Allow multiple entries to be created
            type: Boolean,
            required: false,
            default: false,
        },
        readonly: {
            type: Boolean,
            required: false,
            default: false,
        },
        placeholder: {
            type: String,
            required: false,
        },
        color: {
            type: String,
            required: false,
        },
        datalist: {
            // Display list of suggestions in autocomplete dialog
            type: Array,
            required: false,
        },
    },
    data() {
        return {
            status: "no_optional_text",
        };
    },
    computed: {
        currentValue: {
            get() {
                return this.value;
            },
            set(val) {
                this.setValue(val);
            },
        },
    },
};
</script>
