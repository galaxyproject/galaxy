<script setup lang="ts">
import { BFormRadioGroup } from "bootstrap-vue";
import { computed } from "vue";

interface Props {
    checekd?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "change", value: Props["checekd"]): void;
}>();

const model = computed({
    get: () => props.checekd,
    set: (value) => {
        emit("change", value);
    },
});
</script>

<template>
    <BFormRadioGroup v-model="model" v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BFormRadioGroup>
</template>
