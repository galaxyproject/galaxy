<script setup lang="ts">
import { computed } from "vue";

import { getAppRoot } from "@/onload/loadConfig";

interface WorkflowImageProps {
    workflowId: string;
    size?: string;
}

const props = withDefaults(defineProps<WorkflowImageProps>(), {
    size: "lg",
});

const src = computed(() => {
    return `${getAppRoot()}workflow/gen_image?id=${props.workflowId}&embed=true`;
});
const width = computed(() => {
    const size = props.size;
    if (size == "sm") {
        return "300px";
    } else if (size == "md") {
        return "550px";
    } else {
        return "100%";
    }
});
</script>

<template>
    <img alt="Preview of Galaxy Workflow" :src="src" :width="width" height="auto" />
</template>
