<script setup>
import { computed } from "vue";
import Multiselect from "vue-multiselect";

const props = defineProps({
    disabled: Boolean,
    options: Array,
    value: String,
});

const emit = defineEmits();

const currentValue = computed({
    get: () => props.options.find((option) => option.id === props.value),
    set(newValue) {
        emit("input", newValue.id);
    },
});
</script>

<template>
    <Multiselect v-model="currentValue" :options="options" track-by="id" label="text" />
</template>

<style>
.upload-settings-select {
    width: 150px;
}
</style>
