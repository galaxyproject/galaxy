<script setup lang="ts">
interface PageContainerProps {
    baseClass?: string
}

withDefaults(defineProps<PageContainerProps>(), {
    baseClass: "page-container",
})
</script>
<template>
    <div :class="baseClass">
        <slot></slot>
    </div>
</template>

<style scoped>
.page-container {
    padding: var(--spacing-4);
}
</style>
