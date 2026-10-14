<script setup lang="ts">
interface PageContainerProps {
    baseClass?: string
    /** Constrain the content to a narrow reading column (forms, account pages) */
    narrow?: boolean
}

withDefaults(defineProps<PageContainerProps>(), {
    baseClass: "page-container",
    narrow: false,
})
</script>
<template>
    <div class="page">
        <slot name="header" />
        <div :class="[baseClass, { 'page-container-narrow': narrow }]">
            <slot></slot>
        </div>
    </div>
</template>

<style scoped>
.page-container {
    max-width: var(--shed-content-width);
    margin: 0 auto;
    padding: 1.75rem 1.5rem 3rem;
}

.page-container-narrow {
    max-width: 44rem;
}

@media (max-width: 599px) {
    .page-container {
        padding: 1.25rem 1rem 2rem;
    }
}
</style>
