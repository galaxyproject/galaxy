<script setup lang="ts">
import { BCol, BFormInput, BRow } from "bootstrap-vue";
import { computed } from "vue";

export interface Props {
    id: string;
    value?: string;
}

const props = withDefaults(defineProps<Props>(), {
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
            <BFormInput :id="id" v-model="currentValue" class="cursor-pointer" type="color" size="sm" />
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
