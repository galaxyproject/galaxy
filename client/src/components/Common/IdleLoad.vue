<script setup lang="ts">
// This component delays the rendering of slotted elements
// in order to not slow down the rendering of parent components,
// or the responsiveness of the UI

import { onMounted, ref } from "vue";

import LoadingSpan from "@/components/LoadingSpan.vue";

const props = defineProps<{
    spinner?: boolean;
    center?: boolean;
}>();

const render = ref(false);
const idleFallbackTime = 250;

onMounted(() => {
    if ("requestIdleCallback" in window) {
        window.requestIdleCallback(() => (render.value = true));
    } else {
        setTimeout(() => (render.value = true), idleFallbackTime);
    }
});
</script>

<template>
    <div class="idle-load" :class="{ center: props.center && !render }">
        <slot v-if="render"></slot>
        <LoadingSpan v-else-if="props.spinner" spinner-only />
    </div>
</template>

<style lang="scss" scoped>
.idle-load.center {
    display: grid;
    place-items: center;
}
</style>
