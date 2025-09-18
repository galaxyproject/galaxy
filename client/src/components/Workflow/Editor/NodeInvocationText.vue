<script setup lang="ts">
import { faCheckSquare, faSquare } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormInput } from "bootstrap-vue";
import { sanitize } from "dompurify";

import type { JobState } from "@/api/jobs";
import { isWorkflowInput } from "@/components/Workflow/constants";
import type { GraphStep } from "@/composables/useInvocationGraph";

import InvocationStepStateDisplay from "@/components/WorkflowInvocationState/InvocationStepStateDisplay.vue";

const props = defineProps<{
    invocationStep: GraphStep;
}>();

function isColor(value?: string): boolean {
    return value ? value.match(/^#[0-9a-f]{6}$/i) !== null : false;
}

function textHtml(value: string): string {
    return sanitize(value, { ALLOWED_TAGS: ["b"] });
}

// Helper function to convert the key to JobState type
function toJobState(key: string | number): JobState {
    return key as JobState;
}
</script>
<template>
    <div class="p-1 unselectable">
        <div v-if="props.invocationStep.jobs">
            <div v-for="(value, key) in props.invocationStep.jobs" :key="key">
                <InvocationStepStateDisplay v-if="value !== undefined" :state="toJobState(key)" :job-count="value" />
            </div>
        </div>
        <div v-else-if="isWorkflowInput(props.invocationStep.type)" class="truncate w-100">
            <span v-if="typeof props.invocationStep.nodeText === 'boolean'">
                <FontAwesomeIcon :icon="props.invocationStep.nodeText ? faCheckSquare : faSquare" />
                {{ props.invocationStep.nodeText }}
            </span>
            <span v-else-if="isColor(props.invocationStep.nodeText)" class="d-flex align-items-center">
                <i> {{ props.invocationStep.nodeText }}: </i>
                <BFormInput
                    :value="props.invocationStep.nodeText"
                    class="ml-1 p-0 color-input"
                    type="color"
                    size="sm"
                    readonly />
            </span>
            <!-- eslint-disable vue/no-v-html -->
            <span
                v-else-if="props.invocationStep.nodeText !== undefined"
                v-html="textHtml(props.invocationStep.nodeText)" />
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

    .color-input {
        max-height: 1rem;
    }
}
</style>
