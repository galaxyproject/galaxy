<template>
    <div>
        <b-form-checkbox v-model="currentStatus" class="ui-switch" switch
            >Set value for this optional select field?</b-form-checkbox
        >
        <FormText
            v-if="textEnabled"
            :id="id"
            v-model="currentValue"
            :readonly="readonly"
            :value="value"
            :area="area"
            :placeholder="placeholder"
            :color="color"
            :multiple="multiple"
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
            status: false,
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
        currentStatus: {
            get() {
                return this.status;
            },
            set(val) {
                this.status = val;
                if (val == false) {
                    this.currentValue = null;
                } else {
                    this.currentValue = "";
                }
            },
        },
        textEnabled() {
            return this.currentStatus == true;
        },
    },
    created() {
        this.status = false;
    },
    methods: {
        /** Submits a changed value. */
        setValue(value) {
            this.$emit("input", value, this.id);
            this.$emit("change", this.refreshOnChange);
        },
    },
};
</script>
