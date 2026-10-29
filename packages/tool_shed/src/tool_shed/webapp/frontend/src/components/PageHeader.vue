<script setup lang="ts">
interface PageHeaderProps {
    title?: string
    subtitle?: string
    eyebrow?: string
}

defineProps<PageHeaderProps>()
</script>

<template>
    <div class="page-header shed-brand-backdrop">
        <div class="page-header-inner">
            <div class="page-header-text">
                <p v-if="eyebrow || $slots.eyebrow" class="page-header-eyebrow">
                    <slot name="eyebrow">{{ eyebrow }}</slot>
                </p>
                <h1 class="page-header-title">
                    <slot name="title">{{ title }}</slot>
                </h1>
                <p v-if="subtitle || $slots.subtitle" class="page-header-subtitle">
                    <slot name="subtitle">{{ subtitle }}</slot>
                </p>
                <div v-if="$slots.meta" class="page-header-meta">
                    <slot name="meta" />
                </div>
            </div>
            <div v-if="$slots.actions" class="page-header-actions">
                <slot name="actions" />
            </div>
        </div>
    </div>
</template>

<style scoped>
.page-header {
    color: #fff;
}

.page-header-inner {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1rem 2rem;
    max-width: var(--shed-content-width);
    margin: 0 auto;
    padding: 2rem 1.5rem 1.75rem;
}

.page-header-text {
    flex: 1 1 22rem;
    min-width: 0;
}

/* Not uppercased: the eyebrow often holds an owner's username, which is case-sensitive */
.page-header-eyebrow {
    margin: 0 0 0.4rem;
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--color-ebony-clay-200, #bbc0d2);
}

.page-header-eyebrow :deep(a) {
    color: inherit;
    text-decoration: none;
}

.page-header-eyebrow :deep(a:hover) {
    text-decoration: underline;
    text-decoration-color: currentColor;
}

.page-header-title {
    margin: 0;
    padding-left: 0.85rem;
    border-left: 4px solid var(--shed-gold);
    font-size: clamp(1.6rem, 1.2rem + 1.4vw, 2.25rem);
    font-weight: 700;
    line-height: 1.15;
    color: #fff;
    overflow-wrap: anywhere;
}

.page-header-subtitle {
    margin: 0.6rem 0 0;
    max-width: 48rem;
    font-size: 1.05rem;
    color: var(--color-ebony-clay-100, #d3d6e2);
}

.page-header-subtitle :deep(a) {
    color: #fff;
    text-decoration-color: rgba(255, 255, 255, 0.4);
}

.page-header-subtitle :deep(a:hover) {
    color: var(--shed-gold);
    text-decoration-color: var(--shed-gold);
}

.page-header-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 1rem;
}

.page-header-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
}
</style>
