<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import { isWorkflowInput } from "@/components/Workflow/constants";
import { type GraphStep, iconClasses } from "@/composables/useInvocationGraph";

const props = defineProps<{
    invocationStep: GraphStep;
}>();

const statePlaceholders: Record<string, string> = {
    ok: "successful",
    error: "failed",
};
</script>
<template>
    <div class="p-1 unselectable">
        <div v-if="props.invocationStep.jobs">
            <div v-for="(value, key) in props.invocationStep.jobs" :key="key">
                <span v-if="value !== undefined" class="d-flex align-items-center">
                    <FontAwesomeIcon
                        v-if="iconClasses[key]"
                        :icon="iconClasses[key]?.icon"
                        :class="iconClasses[key]?.class"
                        :spin="iconClasses[key]?.spin"
                        size="sm"
                        class="mr-1" />
                    {{ value }} job{{ value > 1 ? "s" : "" }} {{ statePlaceholders[key] || key }}.
                </span>
            </div>
        </div>
        <div v-else-if="isWorkflowInput(props.invocationStep.type)">
            <!-- TODO: Maybe put a ContentItem here? -->
            This is an input
        </div>
        <div v-else-if="props.invocationStep.type === 'subworkflow'">This is a subworkflow.</div>
        <div v-else>This step has no jobs as of yet.</div>
    </div>
</template>
