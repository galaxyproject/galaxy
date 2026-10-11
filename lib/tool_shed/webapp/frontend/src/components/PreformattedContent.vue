<script setup lang="ts">
interface Props {
    contents: string
}

defineProps<Props>()
</script>

<template>
    <pre class="preformatted-content">{{ contents }}</pre>
</template>

<style scoped>
.preformatted-content {
    margin: 0;
    padding: 0.85rem 1rem;
    font-size: 0.85rem;
    line-height: 1.55;
    /* Tool help is usually fixed-width RST with column tables, so scroll rather than rewrap */
    white-space: pre;
    overflow-x: auto;
    color: var(--shed-text);
    background: color-mix(in srgb, var(--shed-page-bg) 60%, white);
    border: 1px solid var(--shed-border-subtle);
    border-radius: var(--shed-radius-sm);
}
</style>
