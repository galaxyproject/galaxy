<script setup lang="ts">
import { computed } from "vue";

import type { WorkflowInvocationElementView } from "@/api/invocations";

import ParameterStep from "./ParameterStep.vue";

interface Props {
    invocation: WorkflowInvocationElementView;
}

const props = defineProps<Props>();

const parameters = computed(() => {
    const paramsObject = { ...props.invocation.outputs, ...props.invocation.output_collections };
    return Object.entries(paramsObject).map(([key, value]) => {
        return { ...value, label: key };
    });
});
</script>

<template>
    <div>
        <div class="mx-1">
            <ParameterStep data-description="output table" :parameters="parameters" styled-table />
        </div>
    </div>
</template>
