<script setup lang="ts">
import { computed } from "vue";

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
    <b-row>
        <b-col class="form-color-input">
            <b-form-input :id="id" v-model="currentValue" class="cursor-pointer" type="color" size="sm" />
        </b-col>
        <b-col class="pl-0">
            <label class="pt-1 cursor-pointer" :for="id">Select a color</label>
        </b-col>
    </b-row>
</template>

<style scoped>
.form-color-input {
    max-width: 3.6rem;
}
</style>
