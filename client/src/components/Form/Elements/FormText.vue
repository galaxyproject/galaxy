<template>
    <div>
        <b-alert v-if="errorMessage" class="mt-2" :show="dismissCountDown" variant="info" @dismissed="resetAlert">
            {{ errorMessage }}
        </b-alert>
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
                    @change="resetAlert">
                </b-form-textarea>
                <b-form-input
                    v-else
                    :id="id"
                    v-model="currentValue"
                    :class="['ui-input', cls]"
                    :readonly="readonly"
                    :placeholder="placeholder"
                    :style="style"
                    :type="acceptedTypes"
                    :list="`${id}-datalist`"
                    @change="resetAlert">
                </b-form-input>
                <datalist v-if="datalist && !inputArea" :id="`${id}-datalist`">
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
            dismissSecs: 5,
            dismissCountDown: 0,
            errorMessage: "",
        };
    },
    computed: {
        acceptedTypes() {
            return ["text", "password"].includes(this.type) ? this.type : "text";
        },
        currentValue: {
            get() {
                const v = this.value ?? "";
                if (Array.isArray(v)) {
                    if (v.length === 0) {
                        return "";
                    }
                    return this.multiple
                        ? this.value.reduce((str_value, v) => str_value + String(v) + "\n", "")
                        : String(this.value[0]);
                }
                return String(v);
            },
            set(newVal, oldVal) {
                if (newVal !== oldVal) {
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
    methods: {
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
<style scoped>
.ui-input-linked {
    border-left-width: 0.5rem;
}
</style>
