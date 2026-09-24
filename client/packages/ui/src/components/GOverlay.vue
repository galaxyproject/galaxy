<script setup lang="ts">
/**
 * Overlay component that displays a semi-transparent loading overlay
 * over its default slot content. Replaces bootstrap-vue's BOverlay.
 */

withDefaults(
    defineProps<{
        /** Controls overlay visibility */
        show?: boolean;
        /** Overlay background opacity (0-1) */
        opacity?: number;
        /** Disable fade transition */
        noFade?: boolean;
    }>(),
    {
        show: false,
        opacity: 0.6,
        noFade: false,
    },
);
</script>

<template>
    <div class="g-overlay-wrapper position-relative">
        <slot />
        <Transition v-if="!noFade" name="g-overlay-fade">
            <div v-if="show" class="g-overlay" :style="{ '--g-overlay-opacity': opacity }">
                <slot name="overlay">
                    <span class="g-overlay-spinner" />
                </slot>
            </div>
        </Transition>
        <div v-else-if="show" class="g-overlay" :style="{ '--g-overlay-opacity': opacity }">
            <slot name="overlay">
                <span class="g-overlay-spinner" />
            </slot>
        </div>
    </div>
</template>

<style scoped lang="scss">
.g-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, var(--g-overlay-opacity, 0.6));
    border-radius: 0.2rem;
    z-index: 10;
}

.g-overlay-spinner {
    display: inline-block;
    width: 2rem;
    height: 2rem;
    border: 0.25em solid currentColor;
    border-right-color: transparent;
    border-radius: 50%;
    animation: g-overlay-spin 0.75s linear infinite;
    opacity: 0.75;
}

@keyframes g-overlay-spin {
    to {
        transform: rotate(360deg);
    }
}

.g-overlay-fade-enter-active,
.g-overlay-fade-leave-active {
    transition: opacity 0.15s ease;
}

.g-overlay-fade-enter,
.g-overlay-fade-leave-to {
    opacity: 0;
}
</style>
