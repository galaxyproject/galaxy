<script setup>
import { computed } from "vue";
import Select2 from "@/components/Select2.vue";

const props = defineProps({
    disabled: Boolean,
    options: Array,
    value: String,
});

const emit = defineEmits();

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
    <select2 v-model="currentValue" class="upload-settings-select" :enabled="!disabled">
        <option v-for="(option, index) in options" :key="index" :value="option.id">
            {{ option.text }}
        </option>
    </select2>
</template>

<style>
.upload-settings-select {
    width: 150px;
}
</style>
