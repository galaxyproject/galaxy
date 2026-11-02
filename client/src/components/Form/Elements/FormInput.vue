<template>
    <textarea v-if="area" :id="id" v-model="currentValue" class="ui-textarea" />
    <input v-else :id="id" v-model="currentValue" class="ui-input" />
</template>
<script>
export default {
    // Under @vue/compat, keep v-model on modelValue instead of Vue 2's value/input
    compatConfig: { COMPONENT_V_MODEL: false },
    props: {
        id: {
            type: String,
            required: true,
        },
        modelValue: {
            type: String,
            default: "",
        },
        area: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["update:modelValue"],
    computed: {
        currentValue: {
            get() {
                return this.modelValue;
            },
            set(val) {
                this.$emit("update:modelValue", val);
            },
        },
    },
};
</script>
