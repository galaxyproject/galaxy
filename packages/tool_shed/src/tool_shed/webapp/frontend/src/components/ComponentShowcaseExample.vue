<script setup lang="ts">
defineProps({
    title: {
        type: String,
        required: true,
    },
    description: {
        type: String,
        default: "",
    },
})
</script>
<template>
    <div class="component-showcase-example">
        <div class="component-showcase-example-label">
            <span class="component-showcase-example-title">{{ title }}</span>
            <span v-if="description" class="component-showcase-example-description">{{ description }}</span>
        </div>
        <hr />
        <div class="component-showcase-example-body">
            <slot></slot>
        </div>
    </div>
</template>

<style scoped>
.component-showcase-example-label {
    display: flex;
    flex-direction: column;
    width: 100%;
    padding: var(--spacing-2) var(--spacing-4);
}

.component-showcase-example-title {
    font-size: var(--font-size-small);
    color: var(--color-grey-500);
}

.component-showcase-example-description {
    font-size: var(--font-size-small);
    color: var(--color-grey-600);
}

.component-showcase-example-body {
    display: flex;
    flex-direction: column;
    padding: var(--spacing-4);
}
</style>
