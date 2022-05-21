<template>
    <input
        v-if="editable"
        v-model="localValue"
        class="click-to-edit-input"
        contenteditable
        @blur="editable = false"
        @keyup.enter="editable = false" />
    <label v-else @click="editable = true">
        {{ localValue }}
    </label>
</template>

<script>
export default {
    props: {
        value: {
            required: true,
            type: String,
        },
        title: {
            required: false,
            type: String,
        },
    },
    data: function () {
        return {
            editable: false,
            localValue: this.value,
        };
    },
    watch: {
        localValue(newValue) {
            this.$emit("input", newValue);
        },
        value(newValue) {
            this.localValue = newValue;
        },
    },
};
</script>

<style>
.click-to-edit-input {
    width: 600px;
    line-height: 1 !important;
}
</style>
