<template>
    <div>
        <b-alert
            class="mt-2"
            v-if="errorMessage"
            :show="dismissCountDown"
            variant="info"
            @dismissed="dismissCountDown = 0">
            {{ errorMessage }}
        </b-alert>
        <b-row align-v="center">
            <b-col v-if="display == 'radio'">
                <b-form-group>
                    <!-- Select single from radio -->
                    <b-form-radio-group v-model="currentValue" :options="optArray" text-field="label" stacked>
                    </b-form-radio-group>
                </b-form-group>
            </b-col>
            <b-col v-else-if="display == 'checkboxes'">
                <!-- Select multiple from checkboxes -->
                <b-form-group>
                    <b-form-checkbox-group
                        v-model="currentValue"
                        :options="optArray"
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
                    :options="optArray"
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
                    :options="optArray"
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
        optArray() {
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
                if (this.multiple || this.display == "checkboxes") {
                    if (this.value !== "") {
                        const selected = [];
                        if (this.value == null) {
                            return;
                        }
                        let array_val = this.value;
                        // A string is returned if single, but an array if zero or multiple
                        if (!Array.isArray(this.value)) {
                            array_val = [this.value];
                        }
                        for (var i = 0; i < array_val.length; i++) {
                            if (this.display == "checkboxes") {
                                selected.push(this.optArray.find((element) => element.value == array_val[i]).value);
                            } else {
                                selected.push(this.optArray.find((element) => element.value == array_val[i]));
                            }
                        }
                        return selected;
                    } else if (this.defaultValue !== "") {
                        const selected = [];
                        // Create list from default selected values
                        for (var n = 0; n < this.defaultValue.length; n++) {
                            selected.push(this.optArray.find((element) => element.value === this.defaultValue[n]));
                        }
                        return selected;
                        // Return null if value is optional
                    } else {
                        // Try to find a value labeled default in the options
                        for (let x = 0, len = this.optArray.length; x < len; x++) {
                            if (this.optArray[x].default) {
                                return this.optArray[x];
                            }
                        }
                        // Else return first value
                        return this.optArray[0];
                    }

                    // If single select
                } else {
                    // If value provided, use value
                    if (this.value !== "") {
                        if (this.value == null) {
                            return;
                        }
                        if (this.display == "radio") {
                            return this.optArray.find((element) => element.value === this.value).value;
                        } else {
                            return this.optArray.find((element) => element.value === this.value);
                        }
                        // if no value provided, use default value
                    } else if (this.defaultValue !== "") {
                        return this.optArray.find((element) => element.default === this.defaultValue);
                        // If no default value provided and optional is selected, return null
                    } else {
                        for (let i = 0, len = this.optArray.length; i < len; i++) {
                            if (this.optArray[i].default) {
                                return this.optArray[i];
                            }
                        }
                        // Else return first value
                        return this.optArray[0];
                    }
                }
            },
            set(val) {
                // Checkbox is mutliple, but not automatically set. If it IS set, this prevents the multiple from overriding the checkbox
                if (this.multiple && this.display != "checkboxes") {
                    const values = [];
                    for (var i = 0; i < val.length; i++) {
                        values.push(val[i].value);
                    }
                    this.$emit("input", values);
                } else {
                    if (this.display == "radio" || this.display == "checkboxes") {
                        this.$emit("input", val);
                    } else {
                        this.$emit("input", val.value);
                    }
                }
            },
        },
    },
};
</script>
