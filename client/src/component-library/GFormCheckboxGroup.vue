<script setup lang="ts">
import { BFormCheckboxGroup } from "bootstrap-vue";
import { computed } from "vue";

interface Props {
    checked?: any[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "input", value: Props["checked"]): void;
}>();

const model = computed({
    get: () => props.checked,
    set: (value) => {
        emit("input", value);
    },
});
</script>

<template>
    <BFormCheckboxGroup v-model="model" v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BFormCheckboxGroup>
</template>
