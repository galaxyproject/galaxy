<script setup lang="ts">
import { computed, toRef } from "vue";

import WorkflowIcons from "@/components/Workflow/icons";
import { useWorkflowStores } from "@/composables/workflowStores";
import type { Step } from "@/stores/workflowStepStore";
import { parseRequestedToolParts } from "@/utils/tool-version";

import { useStepProps } from "../composables/useStepProps";
import { useUniqueLabelError } from "../composables/useUniqueLabelError";

import FormConditional from "./FormConditional.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import FormCard from "@/components/Form/FormCard.vue";
import FormElement from "@/components/Form/FormElement.vue";

const props = defineProps<{
    step: Step;
}>();

const emit = defineEmits<{
    (e: "onAnnotation", id: number, annotation: string): void;
    (e: "onLabel", id: number, label: string): void;
    (e: "onUpdateStep", id: number, step: Partial<Step>): void;
}>();

const { stepId, contentId, annotation, label, name } = useStepProps(toRef(props, "step"));
const { stepStore } = useWorkflowStores();
const uniqueErrorLabel = useUniqueLabelError(stepStore, label.value);

const toolId = computed(() => contentId?.value || name.value);
const toolParts = computed(() => parseRequestedToolParts(toolId.value));
// the backend only sends tool_version for installed tools, tool shed ids carry it as their last segment
const toolVersion = computed(() => props.step.tool_version || toolParts.value.requested_version);
// the backend sends a plain string here despite the Step typing
const errorMessage = computed(() => String(props.step.errors || "Tool is not installed"));

function onAnnotation(newAnnotation: string) {
    emit("onAnnotation", stepId.value, newAnnotation);
}

function onLabel(newLabel: string) {
    emit("onLabel", stepId.value, newLabel);
}
</script>

<template>
    <FormCard :title="toolParts.name" :icon="WorkflowIcons.tool">
        <template v-slot:body>
            <GAlert variant="warning" show data-description="missing tool alert">
                <p class="font-weight-bold mb-1">{{ errorMessage }}</p>
                <div>
                    Tool ID: <code>{{ toolId }}</code>
                </div>
                <div v-if="toolVersion">Version: {{ toolVersion }}</div>
                <p class="mt-2 mb-0">
                    Its parameters cannot be shown or edited, and the workflow cannot be saved until the tool is
                    installed on this Galaxy or this step is removed.
                </p>
            </GAlert>
            <FormElement
                id="__label"
                :value="label"
                title="Label"
                help="Add a step label."
                :error="uniqueErrorLabel ?? undefined"
                @input="onLabel" />
            <FormElement
                id="__annotation"
                :value="annotation"
                title="Step Annotation"
                :area="true"
                help="Add an annotation or notes to this step. Annotations are available when a workflow is viewed."
                @input="onAnnotation" />
            <FormConditional
                :step="props.step"
                @onUpdateStep="(id: number, s: Partial<Step>) => emit('onUpdateStep', id, s)" />
        </template>
    </FormCard>
</template>
