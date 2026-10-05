<script setup lang="ts">
defineProps({
    title: {
        type: String,
        required: true,
    },
})
</script>

<template>
    <q-page class="bg-secondary window-height window-width row justify-center items-center">
        <div class="column">
            <div class="row">
                <h5 class="text-primary text-h5 q-my-md">{{ title }}</h5>
            </div>
            <div class="row">
                <section class="modal-form-card">
                    <slot></slot>
                </section>
            </div>
        </div>
    </q-page>
</template>

<style scoped>
.modal-form-card {
    background-color: var(--background-color);
    border: 1px solid var(--color-grey-300);
    border-radius: 0;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    padding: var(--spacing-6);
}
</style>
