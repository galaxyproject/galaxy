<script setup lang="ts">
interface Props {
    explanation: string;
}

const props = defineProps<Props>();
</script>

<template>
    <abbr v-g-tooltip.hover :title="props.explanation">
        <slot></slot>
    </abbr>
</template>
