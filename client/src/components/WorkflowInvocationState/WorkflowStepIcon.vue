<script lang="ts" setup>
import {
    faCodeBranch,
    faFile,
    faFolderOpen,
    faPause,
    faPencilAlt,
    faSitemap,
    faWrench,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

// Icon definitions rather than names, since no icons are registered in the FontAwesome library.
const STEP_ICONS = {
    tool: faWrench,
    data_input: faFile,
    data_collection_input: faFolderOpen,
    subworkflow: faSitemap,
    parameter_input: faPencilAlt,
    pause: faPause,
    pick_value: faCodeBranch,
};

interface WorkflowStepIconProps {
    stepType: keyof typeof STEP_ICONS;
}

const props = defineProps<WorkflowStepIconProps>();

const stepIcon = computed(() => STEP_ICONS[props.stepType]);
</script>

<template>
    <FontAwesomeIcon class="mr-1" :icon="stepIcon" :rotation="stepType === 'subworkflow' ? 270 : undefined" />
</template>
