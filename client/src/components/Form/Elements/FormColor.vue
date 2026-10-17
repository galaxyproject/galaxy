<script setup lang="ts">
import { BCol, BRow } from "bootstrap-vue";
import { computed } from "vue";

import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";

export interface FormColorProps {
    value?: string;
    id: string;
}

const props = withDefaults(defineProps<FormColorProps>(), {
    value: "",
});

const emit = defineEmits<{
    (e: "input", value: string): void;
}>();

const currentValue = computed({
    get() {
        return props.value;
    },
    set(newValue) {
        emit("input", newValue);
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
