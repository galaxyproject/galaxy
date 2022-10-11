<template>
    <div>
        <b-alert
            v-if="errorMessage"
            class="mt-2"
            :show="dismissCountDown"
            variant="info"
            @dismissed="dismissCountDown = 0">
            {{ errorMessage }}
        </b-alert>
        <b-row align-v="center">
            <b-col v-if="display == 'radio'">
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
            required: false,
            default: null,
        },
        options: {
            type: Array,
            required: true,
            default: undefined,
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
    data() {
        return {
            // Currently never set?
            errorMessage: "",
        };
    },
    computed: {
        formattedOptions() {
            const formattedOptions = [];
            for (let i = 0, len = this.options.length; i < len; i++) {
                formattedOptions[i] = {
                    label: this.options[i][0],
                    value: this.options[i][1],
                    default: this.options[i][2],
                };
            }
            if (this.multiple == false && this.optional == true) {
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
                    if (this.multiple) {
                        return this.selectValueMultiple(this.value);
                    } else if (this.display == "checkboxes") {
                        return this.selectValueCheckboxes(this.value);
                    } else if (this.display == "radio") {
                        return this.selectValueSingle(this.value);
                    } else {
                        return this.selectValue(this.value);
                    }
                } else if (this.defaultValue !== "") {
                    if (this.multiple || this.display == "checkboxes") {
                        return this.selectValueMultiple(this.defaultValue);
                    } else {
                        return this.selectValue(this.defaultValue);
                    }
                } else {
                    return this.selectDefaultLabelValue();
                }
            },
            set(val) {
                // Checkbox is mutliple, but not automatically set. If it IS set, this prevents the multiple from overriding the checkbox
                if (val == null) {
                    // This case can occur when single-select dropdown is re-selected
                    return;
                } else if (this.multiple && this.display != "checkboxes") {
                    const values = this.getValuesFromFormattedOptions(val);
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
        selectValueMultiple(val) {
            const selected = [];
            const selectedValues = this.normalizeSelectedValues(val);

            for (let i = 0; i < selectedValues.length; i++) {
                selected.push(this.formattedOptions.find((option) => option.value == selectedValues[i]));
            }

            return selected;
        },
        selectValueCheckboxes(val) {
            const selected = [];
            const selectedValues = this.normalizeSelectedValues(val);

            for (let i = 0; i < selectedValues.length; i++) {
                selected.push(this.formattedOptions.find((option) => option.value == selectedValues[i]).value);
            }

            return selected;
        },
        selectValueSingle(val) {
            return this.formattedOptions.find((option) => option.value === val).value;
        },
        selectValue(val) {
            return this.formattedOptions.find((option) => option.value === val);
        },
        selectDefaultLabelValue() {
            // Try to find a value labeled default in the options
            for (let i = 0, len = this.formattedOptions.length; i < len; i++) {
                if (this.formattedOptions[i].default) {
                    return this.formattedOptions[i];
                }
            }

            return this.selectFirstValue();
        },
        selectFirstValue() {
            return this.formattedOptions[0];
        },
        getValuesFromFormattedOptions(options) {
            return Array.isArray(options) ? options.map((option) => option.value) : options;
        },
        normalizeSelectedValues(val) {
            // A string is returned if single, but an array if zero or multiple
            return !Array.isArray(val) ? [val] : val;
        },
    },
};
</script>
