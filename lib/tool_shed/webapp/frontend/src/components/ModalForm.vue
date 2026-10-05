<script setup lang="ts">
import { GHeading } from "@galaxyproject/galaxy-ui"

defineProps({
    title: {
        type: String,
        required: true,
    },
})
</script>

<template>
    <div class="modal-form-backdrop">
        <div class="modal-form-content">
            <GHeading h1 size="lg" class="modal-form-title">{{ title }}</GHeading>
            <section class="modal-form-card">
                <slot></slot>
            </section>
        </div>
    </div>
</template>

<style scoped>
.modal-form-backdrop {
    display: flex;
    justify-content: center;
    align-items: center;
    /* Fill the viewport below the 50px sticky masthead, as q-page did, without a scrollbar */
    min-height: calc(100vh - 50px);
    width: 100%;
    background-color: var(--color-grey-200);
}

.modal-form-content {
    display: flex;
    flex-direction: column;
}

.modal-form-title {
    margin: var(--spacing-4) 0;
    color: var(--color-galaxy-primary);
}

.modal-form-card {
    background-color: var(--background-color);
    border: 1px solid var(--color-grey-300);
    border-radius: 0;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    padding: var(--spacing-6);
}
</style>
