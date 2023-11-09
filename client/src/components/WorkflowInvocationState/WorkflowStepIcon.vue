<script lang="ts" setup>
import { computed } from "vue";

import WorkflowIcons from "@/components/Workflow/icons";

interface WorkflowStepIconProps {
    stepType: "tool" | "data_input" | "data_collection_input" | "subworkflow" | "parameter_input" | "pause";
}

const props = defineProps<WorkflowStepIconProps>();

const stepIcon = computed(() => {
    return WorkflowIcons[props.stepType];
});
const cssClasses = computed(() => {
    return ["fa", "mr-1", stepIcon.value];
});
</script>

<template>
    <i :class="cssClasses"></i>
</template>
