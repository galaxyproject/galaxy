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
    return props.node.errors ? "mini-node-error" : "mini-node-ok";
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
