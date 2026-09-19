<script setup lang="ts">
import { computed } from "vue";

import type { WorkflowInvocationElementView } from "@/api/invocations";

import ParameterStep from "./ParameterStep.vue";

interface Props {
    invocation: WorkflowInvocationElementView;
}

const props = defineProps<Props>();

const parameters = computed(() => {
    const allInputs = { ...props.invocation.inputs, ...props.invocation.input_step_parameters };
    return [...Object.values(allInputs)];
});
</script>

<template>
    <div>
        <div class="mx-1">
            <ParameterStep data-description="input table" :parameters="parameters" styled-table />
        </div>
    </div>
</template>
