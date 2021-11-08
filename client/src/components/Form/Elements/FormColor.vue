<template>
    <b-row>
        <b-col sm="1">
            <b-form-input v-model="currentValue" type="color" size="sm" />
        </b-col>
    </b-row>
</template>

<script>
export default {
    props: {
        value: {
            type: String,
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
    },
};
</script>
