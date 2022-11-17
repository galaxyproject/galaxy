<template>
    <div>
        <b-row align-v="center">
            <b-col v-if="display == 'radio' || display == 'radiobutton'">
                <b-form-group>
                    <!-- Select single from radio -->
                    <b-form-radio-group v-model="currentValue" :options="formattedOptions" text-field="label" stacked>
                    </b-form-radio-group>
                </b-form-group>
            </b-col>
            <b-col v-else-if="display == 'checkboxes'">
                <!-- Select multiple from checkboxes -->
                <b-form-group>
                    <b-form-checkbox-group
                        v-model="currentValue"
                        :options="formattedOptions"
                        value-field="value"
                        text-field="label"
                        stacked>
                    </b-form-checkbox-group>
                </b-form-group>
            </b-col>
            <b-col v-else>
                <!-- Multiple select from drop down -->
                <multiselect
                    v-if="multiple"
                    v-model="currentValue"
                    :options="formattedOptions"
                    :multiple="true"
                    placeholder="Select value"
                    deselect-label=""
                    select-label=""
                    track-by="value"
                    label="label">
                </multiselect>
                <!-- Single select from drop down -->
                <multiselect
                    v-else
                    v-model="currentValue"
                    :options="formattedOptions"
                    deselect-label=""
                    select-label=""
                    label="label"
                    track-by="value">
                    {{ currentValue }}
                </multiselect>
            </b-col>
        </b-row>
    </div>
</template>

<script>
import Multiselect from "vue-multiselect";

export default {
    components: {
        Multiselect,
    },
    props: {
        value: {
            default: null,
        },
        defaultValue: {
            type: [String, Array],
            required: true,
        },
        options: {
            type: Array,
            required: true,
        },
        multiple: {
            type: Boolean,
            required: true,
            default: false,
        },
        display: {
            type: String,
            required: false,
            default: null,
        },
        optional: {
            type: Boolean,
            required: false,
            default: null,
        },
    },
    computed: {
        formattedOptions() {
            const formattedOptions = [];
            this.options.map((option, i) => {
                formattedOptions[i] = {
                    label: option[0],
                    value: option[1],
                    default: option[2],
                };
            });
            if (!this.multiple && this.optional) {
                formattedOptions.unshift({
                    label: "Nothing selected",
                    value: null,
                    default: false,
                });
            }
            return formattedOptions;
        },
        currentValue: {
            get() {
                // My understanding of this is that if we start with a value prop, use it.
                // If there's a defaultValue set, find it in the array and use that.
                // If there's no default value set, use the first item in the array with 'default' set to true.
                // Lastly, just default to the first element in the array.
                if (this.value == null) {
                    return;
                } else if (this.value !== "") {
                    if (this.multiple && this.display != "checkboxes") {
                        return this.selectValueMultiple(this.formattedOptions, this.value);
                    } else if (this.multiple && this.display == "checkboxes") {
                        return this.selectValueCheckboxes(this.formattedOptions, this.value);
                    } else if (this.display == "radio") {
                        return this.selectValueSingle(this.formattedOptions, this.value);
                    } else {
                        return this.selectValue(this.formattedOptions, this.value);
                    }
                } else if (this.defaultValue !== "") {
                    if (this.multiple || this.display == "checkboxes") {
                        return this.selectValueMultiple(this.formattedOptions, this.defaultValue);
                    } else {
                        return this.selectValue(this.formattedOptions, this.defaultValue);
                    }
                } else {
                    return this.selectDefaultLabelValue(this.formattedOptions);
                }
            },
            set(val) {
                // Checkbox is mutliple, but not automatically set. If it IS set, this prevents the multiple from overriding the checkbox
                if (val == null) {
                    // This case can occur when single-select dropdown is re-selected
                    return;
                } else if (this.multiple && this.display != "checkboxes") {
                    const values = this.buildValuesFromFormattedOptions(val);
                    this.$emit("input", values);
                } else if (this.display == "radio" || this.display == "checkboxes") {
                    this.$emit("input", val);
                } else {
                    this.$emit("input", val.value);
                }
            },
        },
    },
    methods: {
        selectValueMultiple(formattedOptions, val) {
            const selectedValues = this.normalizeSelectedValues(val);
            return formattedOptions.filter((option) => selectedValues.indexOf(option.value) > -1);
        },
        selectValueCheckboxes(formattedOptions, val) {
            const selectedValues = this.normalizeSelectedValues(val);
            return formattedOptions
                .filter((option) => selectedValues.indexOf(option.value) > -1)
                .map((option) => option.value);
        },
        selectValueSingle(formattedOptions, val) {
            return formattedOptions.find((option) => option.value === val).value;
        },
        selectValue(formattedOptions, val) {
            return formattedOptions.find((option) => option.value === val);
        },
        selectDefaultLabelValue(formattedOptions) {
            // Try to find a value labeled default in the options
            const formattedOption = [formattedOptions.find((option) => option.default)];
            const selectedOption = formattedOption[0] ?? formattedOptions[0];
            return selectedOption;
        },
        selectFirstValue(formattedOptions) {
            return formattedOptions[0];
        },
        buildValuesFromFormattedOptions(options) {
            return Array.isArray(options) ? options.map((option) => option.value) : options;
        },
        normalizeSelectedValues(val) {
            // A string is returned if single, but an array if zero or multiple
            return !Array.isArray(val) ? [val] : val;
        },
        hasArrayData(data) {
            return Array.isArray(data) && data.length > 0;
        },
    },
};
</script>
