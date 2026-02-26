<script setup lang="ts">
/**
 * A loading overlay with a Galaxy Logo spinner.
 *
 * TODO: Should probably be improved and standardized to become a `GOverlay` component.
 */

import GalaxyLoader from "../GalaxyLoader.vue";

interface Props {
    /** Opacity of the overlay background, between 0 and 1.
     * @default 0.5
     */
    opacity?: number;
    /** Variant of the Galaxy loader.
     * @default "light"
     */
    variant?: "light" | "dark" | "eu";
}

const props = withDefaults(defineProps<Props>(), {
    opacity: 0.5,
    variant: "light",
});
</script>

<template>
    <div class="galaxy-loading-shade" :style="{ '--opacity': props.opacity ?? 0.5 }">
        <div class="galaxy-loading-spinner">
            <GalaxyLoader :variant="props.variant" />
        </div>
    </div>
</template>

<style scoped>
.galaxy-loading-shade {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(255, 255, 255, var(--opacity, 0.5));
    z-index: 10;
    border-radius: 0.2rem;
}

.galaxy-loading-spinner {
    position: sticky;
    top: 50%;
    display: flex;
    justify-content: center;
    transform: translateY(-50%);
}
</style>
