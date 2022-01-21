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
            <b-col>
                <multiselect v-model="currentValue" :options="optArray" label="label" track-by="value" />
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
            type: String,
        },
        defaultValue: {
            type: String,
            required: false,
            default: "",
        },
        options: {
            type: Array,
            required: true,
            default: undefined,
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
            return formattedOptions;
        },
        currentValue: {
            get() {
                // My understanding of this is that if we start with a value prop, use it.
                // If there's a defaultValue set, find it in the array and use that.
                // If there's no default value set, use the first item in the array with 'default' set to true.
                // Lastly, just default to the first element in the array.
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
            },
            set(val) {
                this.$emit("input", val.value);
            },
        },
    },
};
</script>
