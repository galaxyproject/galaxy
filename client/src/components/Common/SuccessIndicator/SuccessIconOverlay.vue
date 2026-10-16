<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { onMounted, ref } from "vue";

import CheckDraw from "./CheckDraw.vue";

const props = defineProps<{
    coveredIcon: IconDefinition;
}>();

const showSuccessBadge = ref(false);

onMounted(() => {
    showSuccessBadge.value = true;
    setTimeout(() => {
        showSuccessBadge.value = false;
    }, 1900);
});
</script>

<template>
    <span class="success-icon-overlay">
        <transition name="success-icon-overlay-fade">
            <CheckDraw v-if="showSuccessBadge" class="success-icon-overlay-check-draw" />
        </transition>
        <FontAwesomeIcon
            v-if="!showSuccessBadge && props.coveredIcon"
            :icon="props.coveredIcon"
            fixed-width
            class="success-icon-overlay-covered" />
    </span>
</template>

<style lang="scss" scoped>
.success-icon-overlay {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.25em;
    height: 1.25em;
}

.success-icon-overlay-check-draw {
    position: absolute;
    inset: 0;
    margin: auto;
}

// Pixel-locked to the same box .success-icon-overlay reserves, so removing this element (when the
// success badge fades in) never changes the wrapper's flex-content width and pushes the tool
// name.
.success-icon-overlay-covered {
    position: absolute;
    inset: 0;
    width: 0.85em;
    height: 0.85em;
    margin: auto;
}

.success-icon-overlay-fade-leave-active {
    transition: opacity 0.4s ease;
}

.success-icon-overlay-fade-leave-to {
    opacity: 0;
}
</style>
