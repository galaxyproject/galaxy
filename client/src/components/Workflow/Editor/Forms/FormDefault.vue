<template>
    <FormCard :title="stepTitle" :icon="nodeIcon">
        <template v-slot:operations>
            <b-button
                v-if="isSubworkflow"
                v-b-tooltip.hover
                role="button"
                title="编辑此子工作流。之后您需要升级此工作流步骤。"
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
                title="将此工作流步骤升级到最新的子工作流版本。"
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
                title="标签"
                help="添加步骤标签。"
                :error="uniqueErrorLabel ?? undefined"
                @input="onLabel" />
            <FormElement
                id="__annotation"
                :value="annotation"
                title="步骤注释"
                :area="true"
                help="为此步骤添加注释或备注。查看工作流时可以看到这些注释。"
                @input="onAnnotation" />
            <FormConditional
                v-if="isSubworkflow"
                :step="step"
                @onUpdateStep="(id, step) => emit('onUpdateStep', id, step)" />
            <FormDisplay
                v-if="configForm?.inputs"
                :id="formDisplayId"
                :key="formKey"
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

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref, toRef, watch } from "vue";

import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import WorkflowIcons from "@/components/Workflow/icons";
import { useWorkflowStores } from "@/composables/workflowStores";
import { useRefreshFromStore } from "@/stores/refreshFromStore";
import type { Step } from "@/stores/workflowStepStore";

import { useStepProps } from "../composables/useStepProps";
import { useUniqueLabelError } from "../composables/useUniqueLabelError";

import FormConditional from "./FormConditional.vue";
import FormCard from "@/components/Form/FormCard.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";
import FormElement from "@/components/Form/FormElement.vue";
import FormOutputLabel from "@/components/Workflow/Editor/Forms/FormOutputLabel.vue";

const props = defineProps<{
    step: Step;
    datatypes: DatatypesMapperModel["datatypes"];
}>();
const emit = defineEmits([
    "onAnnotation",
    "onLabel",
    "onAttemptRefactor",
    "onEditSubworkflow",
    "onSetData",
    "onUpdateStep",
]);
const stepRef = toRef(props, "step");
const { stepId, contentId, annotation, label, name, type, configForm } = useStepProps(stepRef);
const { stepStore } = useWorkflowStores();
const uniqueErrorLabel = useUniqueLabelError(stepStore, label.value);
const stepTitle = computed(() => {
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

// keeps the component from emitting the onCreate change event
const initialChange = ref(true);

function onChange(values: any) {
    if (!initialChange.value) {
        emit("onSetData", stepId.value, {
            id: stepId.value,
            type: type.value,
            content_id: contentId!.value,
            inputs: values,
        });
    }

    initialChange.value = false;
}

const { formKey } = storeToRefs(useRefreshFromStore());
watch(
    () => formKey.value,
    () => (initialChange.value = true)
);
</script>
