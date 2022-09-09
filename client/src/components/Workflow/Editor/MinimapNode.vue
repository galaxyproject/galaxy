<template>
    <rect :x="step.position.left" :y="step.position.top" :width="node.position.width" :height="node.position.height" />
</template>

<script>
export default {
    props: {
        node: {
            type: Object,
        },
        step: {
            type: Object,
        },
    },
};
</script>

<style></style>
