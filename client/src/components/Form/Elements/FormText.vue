<template>
    <b-row align-v="center">
        <b-col>
            <b-form-textarea
                v-if="inputArea"
                :id="id"
                v-model="currentValue"
                :class="['ui-text-area', cls]"
                :readonly="readonly"
                :placeholder="placeholder"
                :style="style"
                @focus="onFocus"
                @blur="onBlur" />
            <b-form-input
                v-else
                :id="id"
                v-model="currentValue"
                :class="['ui-input', cls]"
                :readonly="readonly"
                :placeholder="placeholder"
                :state="showState ? (!currentValue ? (optional ? null : false) : true) : null"
                :style="style"
                :type="acceptedTypes"
                :list="`${id}-datalist`"
                @focus="onFocus"
                @blur="onBlur" />
            <datalist v-if="datalist && !inputArea" :id="`${id}-datalist`">
                <option v-for="data in datalist" :key="data.value" :label="data.label" :value="data.value" />
            </datalist>
        </b-col>
    </b-row>
</template>

<script>
export default {
    props: {
        value: {
            // String; Array for multiple
            default: "",
        },
        id: {
            type: String,
            default: "",
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
            default: "",
        },
        optional: {
            type: Boolean,
            default: true,
        },
        showState: {
            type: Boolean,
            default: false,
        },
        color: {
            type: String,
            default: null,
        },
        cls: {
            // Refers to an optional custom css class name
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
            isFocused: false,
            localValue: "",
        };
    },
    computed: {
        acceptedTypes() {
            return ["text", "password"].includes(this.type) ? this.type : "text";
        },
        currentValue: {
            get() {
                // If focused, return local value to prevent external updates from resetting user input
                if (this.isFocused) {
                    return this.localValue;
                }
                return this.valueToString(this.value);
            },
            set(newVal, oldVal) {
                if (newVal !== oldVal) {
                    // Store the local value while editing
                    this.localValue = newVal;
                    this.$emit("input", newVal);
                }
            },
        },
        inputArea() {
            return this.area || this.multiple;
        },
        style() {
            return this.color
                ? {
                      color: this.color,
                      "border-color": this.color,
                  }
                : null;
        },
    },
    watch: {
        value(newValue) {
            // Only update localValue from prop when not focused
            if (!this.isFocused) {
                this.localValue = this.valueToString(newValue);
            }
        },
    },
    mounted() {
        // Initialize localValue with the initial prop value
        this.localValue = this.valueToString(this.value);
    },
    methods: {
        /**
         * Converts the `FormText` value to a string representation.
         * Handles arrays for multiple inputs and single values.
         */
        valueToString(v) {
            const val = v ?? "";
            if (Array.isArray(val)) {
                if (val.length === 0) {
                    return "";
                }
                return this.multiple
                    ? val.reduce((str_value, item) => str_value + String(item) + "\n", "")
                    : String(val[0]);
            }
            return String(val);
        },
        onFocus() {
            // Set focus state to prevent external updates
            this.isFocused = true;
        },
        onBlur() {
            // When field loses focus, sync with the latest prop value
            this.isFocused = false;
            this.localValue = this.valueToString(this.value);
        },
    },
};
</script>
<style scoped>
.ui-input-linked {
    border-left-width: 0.5rem;
}
</style>
