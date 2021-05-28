<template>
    <div>
        <h2>Library details</h2>
        <pre>{{ localValue }}</pre>
    </div>
</template>

<script>
export default {
    props: {
        value: { type: Object, required: true },
    },
    localValue: {
        get() {
            return this.value;
        },
        set(newValue) {
            this.$emit("input", newValue);
        },
    },
};
</script>
