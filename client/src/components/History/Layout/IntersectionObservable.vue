<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";

const props = defineProps<{
    observer: IntersectionObserver;
}>();

const element = ref<HTMLDivElement>();

onMounted(() => {
    if (element.value) {
        props.observer.observe(element.value);
    }
});

onBeforeUnmount(() => {
    if (element.value) {
        props.observer.unobserve(element.value);
    }
});
</script>

<template>
    <div ref="element">
        <slot></slot>
    </div>
</template>
