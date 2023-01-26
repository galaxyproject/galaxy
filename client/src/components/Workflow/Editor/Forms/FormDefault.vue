<template>
    <FormCard :title="stepTitle" :icon="nodeIcon">
        <template v-slot:operations>
            <b-button
                v-if="isSubworkflow"
                v-b-tooltip.hover
                role="button"
                title="Edit this Subworkflow. You will need to upgrade this Workflow Step afterwards."
                variant="link"
                size="sm"
                class="float-right py-0 px-1"
                @click="onEditSubworkflow">
                <span class="fa fa-pencil-alt" />
            </b-button>
            <b-button
                v-if="isSubworkflow"
                v-b-tooltip.hover
                role="button"
                title="Upgrade this Workflow Step to latest Subworkflow version."
                variant="link"
                size="sm"
                class="float-right py-0 px-1"
                @click="onUpgradeSubworkflow">
                <span class="fa fa-sync" />
            </b-button>
        </template>
        <template v-slot:body>
            <FormElement
                id="__label"
                :value="label"
                title="Label"
                help="Add a step label."
                :error="uniqueErrorLabel"
                @input="onLabel" />
            <FormElement
                id="__annotation"
                :value="annotation"
                title="Step Annotation"
                :area="true"
                help="Add an annotation or notes to this step. Annotations are available when a workflow is viewed."
                @input="onAnnotation" />
            <FormConditional v-if="isSubworkflow" :step="step" v-on="$listeners" />
            <FormDisplay
                v-if="configForm?.inputs"
                :id="formDisplayId"
                :inputs="configForm.inputs"
                @onChange="onChange" />
            <div v-if="isSubworkflow">
                <FormOutputLabel
                    v-for="(output, index) in step.outputs"
                    :key="index"
                    :name="output.name"
                    :step="step"
                    :show-details="true" />
            </div>
        </template>
    </FormCard>
</template>

<script lang="ts" setup>
import FormDisplay from "@/components/Form/FormDisplay.vue";
import FormCard from "@/components/Form/FormCard.vue";
import FormElement from "@/components/Form/FormElement.vue";
import FormOutputLabel from "@/components/Workflow/Editor/Forms/FormOutputLabel.vue";
import FormConditional from "./FormConditional.vue";
import WorkflowIcons from "@/components/Workflow/icons";
import { useWorkflowStepStore, type Step } from "@/stores/workflowStepStore";
import { useUniqueLabelError } from "../composables/useUniqueLabelError";
import { computed, toRef } from "vue";
import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import { useStepProps } from "../composables/useStepProps";

const props = defineProps<{
    step: Step;
    datatypes: DatatypesMapperModel["datatypes"];
}>();
const emit = defineEmits(["onAnnotation", "onLabel", "onAttemptRefactor", "onEditSubworkflow", "onSetData"]);
const stepRef = toRef(props, "step");
const { stepId, contentId, annotation, label, name, type, configForm } = useStepProps(stepRef);
const stepStore = useWorkflowStepStore();
const uniqueErrorLabel = useUniqueLabelError(stepStore, label?.value);
const stepTitle = computed(() => {
    if (label?.value) {
        return label.value;
    }
    if (isSubworkflow.value) {
        return name.value;
    } else {
        return contentId?.value || name.value;
    }
});
const nodeIcon = computed(() => WorkflowIcons[type.value]);
const formDisplayId = computed(() => stepId.value.toString());
const isSubworkflow = computed(() => type.value === "subworkflow");

function onAnnotation(newAnnotation: string) {
    emit("onAnnotation", stepId.value, newAnnotation);
}
function onLabel(newLabel: string) {
    emit("onLabel", stepId.value, newLabel);
}
function onEditSubworkflow() {
    emit("onEditSubworkflow", contentId!.value);
}
function onUpgradeSubworkflow() {
    emit("onAttemptRefactor", [{ action_type: "upgrade_subworkflow", step: { order_index: stepId.value } }]);
}
function onChange(values: any) {
    emit("onSetData", stepId.value, {
        id: stepId.value,
        type: type.value,
        content_id: contentId!.value,
        inputs: values,
    });
}
</script>
