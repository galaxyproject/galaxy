<script setup lang="ts">
import { faArrowCircleLeft, faArrowCircleRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";

interface Props {
    /** The index of the step shown */
    stepIndex: number;
    /** The number of steps in the workflow */
    stepCount: number;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "select", stepIndex: number): void;
}>();
</script>

<template>
    <GButtonGroup>
        <GButton
            title="Previous Step"
            data-description="invocation graph previous step button"
            :disabled="props.stepIndex === 0"
            disabled-title="No Previous Step"
            transparent
            @click="emit('select', props.stepIndex - 1)">
            <FontAwesomeIcon :icon="faArrowCircleLeft" />
            Prev
        </GButton>
        <GButton
            title="Next Step"
            data-description="invocation graph next step button"
            :disabled="props.stepIndex === props.stepCount - 1"
            disabled-title="No More Steps"
            transparent
            @click="emit('select', props.stepIndex + 1)">
            <FontAwesomeIcon :icon="faArrowCircleRight" />
            Next
        </GButton>
    </GButtonGroup>
</template>
