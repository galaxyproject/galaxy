<script setup lang="ts">
import { computed } from "vue";

interface Props {
    text: string;
    maxLength?: number;
}

const props = withDefaults(defineProps<Props>(), {
    maxLength: 24,
});

const trimmedText = computed(() => {
    if (props.text.length > props.maxLength) {
        const partialText = props.text.slice(0, props.maxLength);
        return `${partialText}...`;
    } else {
        return props.text;
    }
});
</script>

<template>
    <span class="text-short-component">
        {{ trimmedText }}
    </span>
</template>

<style scoped>
.text-short-component {
    text-align: center;
    word-wrap: break-word;
}
</style>
