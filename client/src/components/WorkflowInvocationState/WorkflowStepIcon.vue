<script lang="ts" setup>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import WorkflowIcons from "@/components/Workflow/icons";

interface WorkflowStepIconProps {
    stepType: "tool" | "data_input" | "data_collection_input" | "subworkflow" | "parameter_input" | "pause";
}

const props = defineProps<WorkflowStepIconProps>();

const stepIcon = computed(() => {
    return WorkflowIcons[props.stepType];
});
</script>

<template>
    <FontAwesomeIcon class="mr-1" :icon="stepIcon" />
</template>
