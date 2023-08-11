<script setup lang="ts">
import { BFormCheckbox } from "bootstrap-vue";
import { computed } from "vue";

interface Props {
    checked?: any;
    value?: any;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "input", value: Props["checked"] | Props["value"]): void;
}>();

const model = computed({
    get: () => props.checked ?? props.value,
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
