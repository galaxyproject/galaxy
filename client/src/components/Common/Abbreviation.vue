<script setup lang="ts">
const props = defineProps<{ explanation: string }>();
</script>

<template>
    <abbr v-b-tooltip.hover :title="props.explanation">
        <slot></slot>
    </abbr>
</template>
