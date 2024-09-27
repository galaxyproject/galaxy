<script setup lang="ts">
import type { Step } from "@/stores/workflowStepStore";

import Heading from "@/components/Common/Heading.vue";

const props = defineProps<{
    step: Step;
}>();
</script>

<template>
    <section class="tool-inspector">
        <Heading h2 size="md">
            {{ props.step.name }}
        </Heading>
    </section>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.tool-inspector {
    --clearance: 8px;
    --width: 300px;

    position: absolute;
    right: 0;
    top: var(--clearance);
    bottom: var(--clearance);
    width: var(--width);

    background-color: $white;

    z-index: 50000;
    border-color: $border-color;
    border-width: 1px;
    border-style: solid;
    border-radius: 0.5rem 0 0 0.5rem;
    padding: 0.25rem 0.5rem;
}
</style>
