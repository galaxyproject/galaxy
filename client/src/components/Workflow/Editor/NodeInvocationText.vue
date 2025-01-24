<script setup lang="ts">
import { faCheckSquare, faSquare } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import { isWorkflowInput } from "@/components/Workflow/constants";
import { type GraphStep, iconClasses, statePlaceholders } from "@/composables/useInvocationGraph";

const props = defineProps<{
    invocationStep: GraphStep;
}>();
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
        <div v-else-if="isWorkflowInput(props.invocationStep.type)" class="truncate w-100">
            <span v-if="typeof props.invocationStep.nodeText === 'boolean'">
                <FontAwesomeIcon :icon="props.invocationStep.nodeText ? faCheckSquare : faSquare" />
                {{ props.invocationStep.nodeText }}
            </span>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <span v-else-if="props.invocationStep.nodeText !== undefined" v-html="props.invocationStep.nodeText" />
            <span v-else>This is an input</span>
        </div>
        <div v-else-if="props.invocationStep.type === 'subworkflow'">This is a subworkflow.</div>
        <div v-else>This step has no jobs as of yet.</div>
    </div>
</template>

<style scoped>
.truncate {
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
}
</style>
