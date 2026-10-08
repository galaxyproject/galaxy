<script setup lang="ts">
import { GHeading } from "@galaxyproject/galaxy-ui"
import { useAttrs } from "vue"

const attrs = useAttrs()
</script>

<template>
    <section class="component-showcase">
        <div class="component-showcase-header">
            <GHeading h2 size="md" class="component-showcase-title">{{ attrs.title }}</GHeading>
        </div>
        <hr />
        <slot></slot>
    </section>
</template>

<style scoped>
.component-showcase {
    margin: var(--spacing-6) 0;
    background-color: var(--background-color);
    border: 1px solid var(--color-grey-300);
    border-radius: 0.25rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.component-showcase-header {
    padding: var(--spacing-4);
}
</style>
