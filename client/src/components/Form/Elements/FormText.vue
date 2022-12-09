<template>
    <div>
        <b-alert v-if="errorMessage" class="mt-2" :show="dismissCountDown" variant="info" @dismissed="resetAlert">
            {{ errorMessage }}
        </b-alert>
        <b-row align-v="center">
            <b-col>
                <component
                    :is="componentName"
                    :id="id"
                    v-model="currentValue"
                    class="text-input"
                    :readonly="readonly"
                    :placeholder="placeholder"
                    :style="style"
                    :type="localType"
                    @change="onInputChange" />

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
        styleObj: {
            // This will be applied to the input element
            type: Object,
            required: false,
            default: () => {},
        },
        datalist: {
            // Display list of suggestions in autocomplete dialog
            type: Array,
            required: false,
        },

        // These last three are for handling special input cases only

        optional: {
            type: Boolean,
            default: false,
            required: false,
        },
        model_class: {
            type: String,
            required: false,
        },
        data: {
            type: Object, // ?
            required: false,
        },
    },
    data() {
        let inputArea;
        if (["SelectTagParameter", "ColumnListParameter"].includes(this.model_class) || (this.options && this.data)) {
            inputArea = this.multiple;
        }
        return {
            dismissSecs: 5,
            dismissCountDown: 0,
            errorMessage: "",
            inputArea: inputArea,
        };
    },
    computed: {
        localType() {
            // this seems silly, if we're in a component called FormText ... this has to be text??
            if (this.inputArea) {
                return "text";
            }
            return this.type;
        },
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
            // TODO: handle the emmitted "input"
            set(newVal, oldVal) {
                if (newVal !== oldVal) {
                    this.$emit("input", newVal);
                }
            },
        },
        componentName() {
            return this.area || this.multiple ? "b-form-textarea" : "b-form-input";
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
