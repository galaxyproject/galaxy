<script setup lang="ts">
import { faSpinner } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"

interface LoadingProps {
    message?: string
}

withDefaults(defineProps<LoadingProps>(), {
    message: "Loading",
})
</script>

<template>
    <div class="q-pa-md" role="status" aria-live="polite" aria-busy="true">
        <div class="fit q-gutter-md row loading-row">
            <FontAwesomeIcon :icon="faSpinner" spin class="loading-spinner" aria-hidden="true" />
            <span class="loading-message">{{ message }}.<span class="blinking">..</span></span>
        </div>
    </div>
</template>

<style scoped>
.loading-row {
    align-items: center;
}

.loading-spinner {
    font-size: 4em;
    color: var(--color-blue-500);
}

.loading-message {
    font-size: 2em;
    color: var(--color-blue-500);
}

.blinking {
    animation: blinker 1s linear infinite;
}

@keyframes blinker {
    50% {
        opacity: 0;
    }
}
</style>
