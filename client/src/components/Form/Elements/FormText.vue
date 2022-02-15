<template>
    <div>
        <b-alert class="mt-2" v-if="errorMessage" :show="dismissCountDown" variant="info" @dismissed="resetAlert">
            {{ errorMessage }}
        </b-alert>
        <b-row align-v="center">
            <b-col>
                <!-- type        <str> "text" or "password" -->
                <!-- area        <bool> presumably for a textarea instead of input -->
                <!-- readonly    <bool> -->
                <!-- color       <str> -->
                <!-- styleObj    <obj> applied to input element -->
                <!-- placeholder <str> -->
                <!-- datalist    <arr> -->

                <!-- multiple <bool>
                     Allow multiple entries to be created?
                     Seems to use a textarea currently... line separated values?
                 -->

                <component
                    :is="componentName"
                    :id="id"
                    :readonly="readonly"
                    :placeholder="placeholder"
                    :style="style"
                    :type="type"
                    v-model="currentValue"
                    @change="onInputChange" />

                <datalist v-if="datalist && !area && !multiple" :id="`${id}-datalist`">
                    <option v-for="d in datalist" value="d"></option>
                </datalist>
            </b-col>
        </b-row>
    </div>
</template>

<script>
export default {
    props: {
        value: {
            // String or Array for multiple
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
            validator: (prop) => ["text", "password"].includes(prop.toLowerCase()),
        },
        area: {
            type: Boolean,
            required: false,
            default: false,
        },
        multiple: {
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
            type: Object,
            required: false,
            default: () => {},
        },
        datalist: {
            // Display list of suggestions in autocomplete dialog
            type: Array,
            required: false,
        },
    },
    data() {
        return {
            dismissSecs: 5,
            dismissCountDown: 0,
            errorMessage: "",
        };
    },
    computed: {
        currentValue: {
            get() {
                // TODO: is silent fail on non-strings appropriate?
                const v = this.value || "";
                if (typeof v === "array") {
                    return this.multiple ? v.map((i) => String(i)).join("\n") : String(v[0]);
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
            // Some validation?

            // Could we accept a validation function in props?

            // if (value !== xxx) {
            //     // Show some info alert
            // }
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
