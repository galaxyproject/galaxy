<template>
    <b-form-checkbox v-model="currentValue" class="no-highlight" switch>
        {{ label }}
    </b-form-checkbox>
</template>

<script>
export default {
    props: {
        value: {
            required: true,
        },
    },
    computed: {
        currentValue: {
            get() {
                return ["true", true].includes(this.value);
            },
            set(val) {
                this.$emit("input", val);
            },
        },
        label() {
            return this.currentValue ? "Yes" : "No";
        },
    },
};
</script>
