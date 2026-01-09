<script setup lang="ts">
import type { BreadcrumbItem } from "./index";

interface Props {
    items: BreadcrumbItem[];
}

defineProps<Props>();

const emit = defineEmits<{
    (e: "navigate", index: number): void;
}>();

function handleNavigate(index: number | undefined) {
    if (index !== undefined) {
        emit("navigate", index);
    }
}
</script>

<template>
    <nav aria-label="breadcrumb" class="breadcrumb-nav">
        <template v-for="(item, idx) in items">
            <button
                v-if="idx < items.length - 1"
                :key="`link-${idx}`"
                v-b-tooltip.hover.noninteractive
                class="breadcrumb-link"
                :title="`Navigate to ${item.title}`"
                @click="handleNavigate(item.index)">
                {{ item.title }}
            </button>
            <span v-else :key="`current-${idx}`" class="breadcrumb-current-label" aria-current="page">
                {{ item.title }}
            </span>
            <span v-if="idx < items.length - 1" :key="`sep-${idx}`" class="breadcrumb-separator"> / </span>
        </template>
    </nav>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.breadcrumb-nav {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    row-gap: 0.5rem;
}

.breadcrumb-link {
    background: none;
    border: none;
    color: $brand-primary;
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 250px;

    &:hover {
        background-color: rgba($brand-primary, 0.1);
        text-decoration: underline;
    }
}

.breadcrumb-current-label {
    font-weight: 600;
    padding: 0.25rem 0.5rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 250px;
}

.breadcrumb-separator {
    color: $text-muted;
    padding: 0 0.25rem;
    flex-shrink: 0;
}
</style>
