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
            <b-col v-if=" display == null">
                <!-- Single select from drop down -->
                <multiselect
                    v-if=" multiple == false"
                    v-model="currentValue"
                    :options="optArray"
                    :allow-empty="false"
                    deselect-label=""
                    select-label=""
                    label="label"
                    track-by="value"> {{ currentValue }} </multiselect>
                <!-- Multiple select from drop down -->
                <multiselect
                    v-else-if=" multiple == true"
                    v-model="currentValue"
                    :options="optArray"
                    :multiple="true"
                    placeholder="Select value"
                    deselect-label=""
                    select-label="Selected"
                    label="label"
                    track-by="value"
                    >
                </multiselect>
            </b-col>
            <b-col v-else-if=" display == 'radio'">
                <b-form-group>
                    <!-- Select single from checkboxes -->
                    <b-form-radio-group
                        v-if="multiple == false"
                        v-model="currentValue"
                        :options="optArray"
                        text-field="label"
                        value-field="value"
                        stacked>
                    </b-form-radio-group>

                    <!-- Select multiple from checkboxes -->
                    <b-form-checkbox-group
                        v-if="multiple == true"
                        v-model="currentValue"
                        :options="optArray"
                        value-field="value"
                        text-field="label"
                        stacked>
                    </b-form-checkbox-group>
                </b-form-group>
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
            required: true,
            type: [String, Array],
        },
        defaultValue: {
            type: [String, Array],
            required: false,
            default: "",
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
        }
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
            return formattedOptions;
        },
        currentValue: {
            get() {
                // My understanding of this is that if we start with a value prop, use it.
                // If there's a defaultValue set, find it in the array and use that.
                // If there's no default value set, use the first item in the array with 'default' set to true.
                // Lastly, just default to the first element in the array.
                if(this.multiple) { 
                    if (this.value !== "") {
                        let selected = [];
                        for(var i = 0; i < this.value.length; i++){
                            if(selected.includes(this.value[i])){
                                selected = selected.filter((element) => element === this.value[i].value)
                            } else {
                                selected.push(this.optArray.find((element) => element.value === this.value[i]).value);
                            }
                        }
                        return selected;
                    } else if (this.defaultValue !== "") {
                        let selected = [];
                        for(var i = 0; i < this.defaultValue.length; i++){
                            selected.push(this.optArray.find((element) => element.value === this.defaultValue[i]));
                        }
                        return selected;
                    } else {
                        for (let i = 0, len = this.optArray.length; i < len; i++) {
                            if (this.optArray[i].default === true) {
                                return this.optArray[i];
                            }
                        }
                        return this.optArray[0];
                    }
                } else {
                    if (this.value !== "") {
                        return this.optArray.find((element) => element.value === this.value);
                    } else if (this.defaultValue !== "") {
                        return this.optArray.find((element) => element.default === this.defaultValue);
                    } else {
                        for (let i = 0, len = this.optArray.length; i < len; i++) {
                            if (this.optArray[i].default === true) {
                                return this.optArray[i];
                            }
                        }
                        return this.optArray[0];
                    }
                }
            },
            set(val) {
                if (this.multiple){
                    this.$emit("input", val);
                }
                else {
                    this.$emit("input", val.value);
                }
            },
        },
    },
};
</script>
<style>
.multiselect__option--selected.multiselect__option--highlight {
    color: #2c3143 !important;
    background: #dee2e6 !important;
}
</style>
