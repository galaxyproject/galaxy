<template>
    <b-form-checkbox v-model="currentValue" class="no-highlight" switch>
        <span>{{ label }}</span>
    </b-form-checkbox>
</template>

<script>
export default {
    props: {
        value: {
            type: Boolean,
            required: true,
        },
    },
    computed: {
        currentValue: {
            get() {
                return this.value;
            },
            set(val) {
                this.$emit("input", val);
            },
        },
        label() {
            return this.value ? "Yes" : "No";
        },
    },
};
</script>
