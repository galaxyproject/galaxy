<script setup lang="ts">
import { BCol, BRow } from "bootstrap-vue";
import { computed } from "vue";

import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";

export interface FormColorProps {
    modelValue?: string;
    id: string;
}

defineOptions({
    // Under @vue/compat, keep v-model on modelValue instead of Vue 2's value/input
    compatConfig: { COMPONENT_V_MODEL: false },
});

const props = withDefaults(defineProps<FormColorProps>(), {
    modelValue: "",
});

const emit = defineEmits<{
    (e: "update:modelValue", value: string): void;
}>();

const currentValue = computed({
    get() {
        return props.modelValue;
    },
    set(newValue) {
        emit("update:modelValue", newValue);
    },
});
</script>

<template>
    <BRow>
        <BCol class="form-color-input">
            <GFormInput :id="id" v-model="currentValue" class="cursor-pointer" type="color" size="small" />
        </BCol>
        <BCol class="pl-0">
            <label class="pt-1 cursor-pointer" :for="id">Select a color</label>
        </BCol>
    </BRow>
</template>

<style scoped>
.form-color-input {
    max-width: 3.6rem;
}
</style>
