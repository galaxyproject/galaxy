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
                <q-card square bordered class="q-pa-lg shadow-1">
                    <slot></slot>
                </q-card>
            </div>
        </div>
    </q-page>
</template>
