<script setup lang="ts">
import { computed } from "vue";

import { getAppRoot } from "@/onload/loadConfig";

interface WorkflowImageProps {
    workflowId: string;
    workflowVersion?: string;
    size?: string;
}

const props = withDefaults(defineProps<WorkflowImageProps>(), {
    size: "lg",
    workflowVersion: undefined,
});

const src = computed(() => {
    let extraArgs = "";
    if (props.workflowVersion) {
        extraArgs = `&version=${props.workflowVersion}`;
    }
    return `${getAppRoot()}workflow/gen_image?id=${props.workflowId}&embed=true${extraArgs}`;
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
