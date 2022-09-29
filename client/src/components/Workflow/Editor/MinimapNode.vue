<script setup>
import { computed } from "vue";

const props = defineProps({
    node: {
        type: Object,
    },
    step: {
        type: Object,
    },
});

const nodeClass = computed(() => {
    const stateClass = props.node.errors ? "error" : "ok";
    const highlightClass = props.node.isActive ? "highlight" : "";
    return [stateClass, highlightClass];
});
</script>
<template>
    <rect
        :class="nodeClass"
        :x="step.position.left"
        :y="step.position.top"
        :width="node.position.width"
        :height="node.position.height" />
</template>
