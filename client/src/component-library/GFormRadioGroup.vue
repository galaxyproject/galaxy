<script setup lang="ts">
import { BFormRadioGroup } from "bootstrap-vue";
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
    <BFormRadioGroup v-model="model" v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BFormRadioGroup>
</template>
