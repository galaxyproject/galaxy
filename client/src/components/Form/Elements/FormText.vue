<template>
    <div>
        <b-alert v-if="errorMessage" class="mt-2" :show="dismissCountDown" variant="info" @dismissed="resetAlert">
            {{ errorMessage }}
        </b-alert>
        <b-row align-v="center">
            <b-col>
                <b-form-textarea
                    v-if="this.area || this.multiple"
                    :id="id"
                    v-model="currentValue"
                    class="text-input"
                    :readonly="readonly"
                    :placeholder="placeholder"
                    :style="style"
                    :type="type"
                    @change="onInputChange">
                </b-form-textarea>
                <b-form-input
                    v-else
                    :id="id"
                    v-model="currentValue"
                    class="text-input"
                    :readonly="readonly"
                    :placeholder="placeholder"
                    :style="style"
                    :type="type"
                    @change="onInputChange">
                </b-form-input>
                <datalist v-if="datalist && !inputArea && !multiple" :id="`${id}-datalist`">
                    <option v-for="data in datalist" :key="data.value" :label="data.label" :value="data.value"></option>
                </datalist>
            </b-col>
        </b-row>
    </div>
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
        color: {
            type: String,
            default: "",
        },
        styleObj: {
            // This will be applied to the input element
            type: Object,
            default: () => {},
        },
        datalist: {
            // Display list of suggestions in autocomplete dialog
            type: Array,
            default: null,
        },

        // These last three are for handling special input cases only

        optional: {
            type: Boolean,
            default: false,
        },
        model_class: {
            type: String,
            default: "",
        },
        data: {
            type: Object, // ?
            default: () => {},
        },
    },
    data() {
        const inputArea =
            this.multiple &&
            (["SelectTagParameter", "ColumnListParameter"].includes(this.model_class) || (this.options && this.data));
        return {
            dismissSecs: 5,
            dismissCountDown: 0,
            errorMessage: "",
            inputArea: inputArea,
        };
    },
    computed: {
        currentValue: {
            get() {
                // TODO: is silent fail on non-strings appropriate?
                const v = this.value || "";
                if (Array.isArray(v)) {
                    return this.multiple
                        ? this.value.reduce((str_value, v) => str_value + String(v) + "\n", "")
                        : String(this.value[0]);
                }
                return typeof v === "string" ? v : "";
            },
            set(newVal, oldVal) {
                if (newVal !== oldVal) {
                    this.$emit("input", newVal);
                }
            },
        },
        style() {
            return this.color ? { ...this.styleObj, color: this.color } : this.styleObj;
        },
    },
    methods: {
        onInputChange(value) {
            this.resetAlert();
        },
        showAlert(error) {
            if (error) {
                this.errorMessage = error;
                this.dismissCountDown = this.dismissSecs;
            }
        },
        resetAlert() {
            this.dismissCountDown = 0;
        },
    },
};
</script>
