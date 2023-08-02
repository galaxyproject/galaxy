<script setup lang="ts">
import { BFormCheckbox } from "bootstrap-vue";
import { computed } from "vue";

interface Props {
    value: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "input", value: Props["value"]): void;
}>();

const model = computed({
    get: () => props.value,
    set: (value) => {
        emit("input", value);
    },
});
</script>

<template>
    <BFormCheckbox v-model="model" v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BFormCheckbox>
</template>
