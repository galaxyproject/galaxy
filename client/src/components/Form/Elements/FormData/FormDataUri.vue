<template>
    <b-row align-v="center">
        <b-col>
            <b-form-input :id="id" v-model="displayValue" :class="['ui-input', cls]" :readonly="true" />
        </b-col>
    </b-row>
</template>

<script>
export default {
    props: {
        value: {
            type: Object,
        },
        id: {
            type: String,
            default: "",
        },
        multiple: {
            type: Boolean,
            default: false,
        },
        cls: {
            // Refers to an optional custom css class name
            type: String,
            default: null,
        },
    },
    computed: {
        displayValue: {
            get() {
                return this.value.url;
            },
            set(newVal, oldValue) {
                if (newVal !== this.value.url) {
                    this.$emit("input", this.value);
                }
            },
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
    },
};
</script>
<style scoped>
.ui-input-linked {
    border-left-width: 0.5rem;
}
</style>
