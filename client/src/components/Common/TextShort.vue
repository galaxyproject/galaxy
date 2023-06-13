<script setup lang="ts">
import { computed } from "vue";

const props = defineProps({
    text: {
        type: String,
        required: true,
    },
    maxLength: {
        type: Number,
        default: 24,
    },
});
const text = computed(() => {
    if (props.text.length > props.maxLength) {
        const partialText = props.text.slice(0, props.maxLength);
        return `${partialText}...`;
    } else {
        return props.text;
    }
});
</script>

<template>
    <span class="text-break text-center">
        {{ text }}
    </span>
</template>
