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
            <section class="modal-form-card">
                <GHeading h1 size="lg" class="modal-form-title">{{ title }}</GHeading>
                <slot></slot>
            </section>
        </div>
    </div>
</template>

<style scoped>
/* Account pages sit on the brand's dark grid backdrop, with the form on a single white card */
.modal-form-backdrop {
    display: flex;
    justify-content: center;
    align-items: flex-start;
    min-height: calc(100vh - var(--shed-masthead-height));
    width: 100%;
    padding: clamp(2rem, 8vh, 5rem) 1rem 3rem;
    background-color: var(--color-galaxy-dark, #2c3143);
    background-image:
        linear-gradient(to right, rgba(255, 255, 255, 0.04) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(255, 255, 255, 0.04) 1px, transparent 1px),
        linear-gradient(135deg, var(--color-galaxy-dark, #2c3143) 0%, var(--color-galaxy-primary, #25537b) 100%);
    background-size:
        24px 24px,
        24px 24px,
        auto;
}

.modal-form-content {
    width: min(26rem, 100%);
}

.modal-form-card {
    padding: 2rem 2rem 1.5rem;
    background-color: var(--shed-surface);
    border-top: 4px solid var(--shed-gold);
    border-radius: var(--shed-radius);
    box-shadow:
        0 20px 50px rgba(10, 14, 28, 0.35),
        0 2px 6px rgba(10, 14, 28, 0.2);
}

.modal-form-title {
    margin: 0 0 1.25rem;
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--shed-heading);
}

/* Sections the account pages put in the card: the form, then a centered footer of links */
:slotted(.modal-form-section-footer) {
    margin-top: 1.5rem;
    padding-top: 1rem;
    text-align: center;
    border-top: 1px solid var(--shed-border-subtle);
}

:slotted(.modal-form-footer-text) {
    margin: 0.35rem 0;
    font-size: 0.92rem;
    color: var(--shed-muted);
}

@media (max-width: 599px) {
    .modal-form-card {
        padding: 1.5rem 1.25rem 1.25rem;
    }
}
</style>
