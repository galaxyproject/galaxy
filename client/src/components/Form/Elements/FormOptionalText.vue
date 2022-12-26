<template>
    <div>
        <b-form-checkbox v-model="currentStatus" class="ui-switch" switch>
            Set value for this optional select field?
        </b-form-checkbox>
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
            default: "",
        },
        id: {
            type: String,
            default: null,
        },
        type: {
            type: String,
            default: "text",
        },
        area: {
            // <textarea> instead of <input> element
            type: Boolean,
            default: false,
        },
        multiple: {
            // Allow multiple entries to be created
            type: Boolean,
            default: false,
        },
        readonly: {
            type: Boolean,
            default: false,
        },
        placeholder: {
            type: String,
            default: null,
        },
        color: {
            type: String,
            default: null,
        },
        datalist: {
            // Display list of suggestions in autocomplete dialog
            type: Array,
            default: null,
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
    methods: {
        /** Submits a changed value. */
        setValue(value) {
            this.$emit("input", value, this.id);
            this.$emit("change", this.refreshOnChange);
        },
    },
};
</script>
