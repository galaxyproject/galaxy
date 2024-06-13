<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref, toRef, watch } from "vue";

import { useStepProps } from "@/components/Workflow/Editor/composables/useStepProps";
import { useUniqueLabelError } from "@/components/Workflow/Editor/composables/useUniqueLabelError";
import { useWorkflowStores } from "@/composables/workflowStores";
import { useRefreshFromStore } from "@/stores/refreshFromStore";
import type { PostJobActions, Step } from "@/stores/workflowStepStore";
import Utils from "@/utils/utils";

import Heading from "@/components/Common/Heading.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";
import FormElement from "@/components/Form/FormElement.vue";
import ToolCard from "@/components/Tool/ToolCard.vue";
import FormConditional from "@/components/Workflow/Editor/Forms/FormConditional.vue";
import FormSection from "@/components/Workflow/Editor/Forms/FormSection.vue";

interface Props {
    step: Step;
    dataTypes: string[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "onSetData", stepId: number, data: any): void;
    (e: "onLabel", stepId: number, label: string): void;
    (e: "onUpdateStep", stepId: string, step: Step): void;
    (e: "onAnnotation", stepId: number, annotation: string): void;
    (e: "onChangePostJobActions", stepId: number, postJobActions: PostJobActions): void;
}>();

const { stepId, annotation, label, stepInputs, stepOutputs, configForm, postJobActions } = useStepProps(
    toRef(props, "step")
);
const { stepStore } = useWorkflowStores();
const { formKey } = storeToRefs(useRefreshFromStore());
const uniqueErrorLabel = useUniqueLabelError(stepStore, label.value);

const messageText = ref("");
const mainValues = ref(null);
const messageVariant = ref("success");

const id = computed(() => {
    // Make sure we compute a unique id. Local tools don't include the version in the id,
    // but updating tool form when switching tool versions requires that the id changes.
    // (see https://github.com/galaxyproject/galaxy/blob/f5e07b11f0996e75b2b6f27896b2301d8fa8717d/client/src/components/Form/FormDisplay.vue#L108)
    return `${stepId.value}:${configForm.value?.id}/${configForm.value?.version}`;
});
const hasData = computed(() => {
    return !!configForm.value?.id;
});
const errors = computed(() => {
    return configForm.value?.errors || { ...props.step.errors };
});
const inputs = computed(() => {
    const inputs = configForm.value?.inputs;

    if (!inputs) {
        return [];
    }

    Utils.deepEach(inputs, (input: any) => {
        if (input.type) {
            if (["data", "data_collection"].indexOf(input.type) != -1) {
                const extensions = Array.isArray(input.extensions) ? Utils.textify(input.extensions) : "";

                input.titleonly = true;
                input.info = `Data input '${input.name}' (${extensions})`;
                input.value = { __class__: "RuntimeValue" };
            } else {
                input.connectable = ["rules"].indexOf(input.type) == -1;
                input.collapsible_value = {
                    __class__: "RuntimeValue",
                };
                input.is_workflow =
                    (input.options && input.options.length === 0) || ["integer", "float"].indexOf(input.type) != -1;
            }
        }
    });

    Utils.deepEach(inputs, (input: any) => {
        if (input.type === "conditional") {
            input.connectable = false;
            input.test_param.collapsible_value = undefined;
        }
    });

    return inputs;
});

function onAnnotation(newAnnotation: string) {
    emit("onAnnotation", stepId.value, newAnnotation);
}

function onLabel(newLabel: string) {
    emit("onLabel", stepId.value, newLabel);
}

/**
 * Change event is triggered on component creation and input changes.
 * @param { Object } values contains flat key-value pairs `prefixed-name=value`
 */
function onChange(values: any) {
    mainValues.value = values;
    const initialRequest = mainValues.value === null;

    if (!initialRequest) {
        postChanges();
    }
}

function onChangePostJobActions(postJobActions: PostJobActions) {
    emit("onChangePostJobActions", stepId.value, postJobActions);
}

function onChangeVersion(newVersion: string) {
    messageText.value = `Now you are using '${configForm.value?.name}' version ${newVersion}.`;

    postChanges(newVersion);
}

function onUpdateFavorites(user: any, newFavorites: any) {
    user.preferences["favorites"] = newFavorites;
}

function postChanges(newVersion?: string) {
    const payload = Object.assign({}, mainValues.value);
    const options = configForm.value;

    let toolId = options?.id;
    let toolVersion = options?.version;

    if (newVersion) {
        toolId = toolId.replace(toolVersion, newVersion);
        toolVersion = newVersion;
    }

    emit("onSetData", stepId.value, {
        tool_id: toolId,
        tool_version: toolVersion,
        type: "tool",
        inputs: payload,
    });
}

function onUpdateStep(step: Step) {
    emit("onUpdateStep", id.value, step);
}

watch(
    () => formKey.value,
    () => (mainValues.value = null)
);
</script>

<template>
    <ToolCard
        :id="configForm?.id || step.content_id"
        :version="configForm?.version"
        :title="configForm?.name || step.name"
        :description="configForm?.description"
        :options="configForm"
        :message-text="messageText"
        :message-variant="messageVariant"
        :step-error="step.errors"
        @onChangeVersion="onChangeVersion"
        @onUpdateFavorites="onUpdateFavorites">
        <template v-slot:body>
            <FormElement
                id="__label"
                :disabled="!hasData"
                :value="label"
                title="Label"
                help="Add a step label."
                :error="uniqueErrorLabel"
                @input="onLabel" />

            <FormElement
                id="__annotation"
                :disabled="!hasData"
                :value="annotation"
                title="Step Annotation"
                :area="true"
                help="Add an annotation or notes to this step. Annotations are available when a workflow is viewed."
                @input="onAnnotation" />

            <FormConditional :step="step" @onUpdateStep="onUpdateStep" />

            <div v-if="inputs.length" class="mt-2 mb-4">
                <Heading h2 separator bold size="sm"> Tool Parameters </Heading>

                <FormDisplay
                    :id="id"
                    :key="formKey"
                    :inputs="inputs"
                    :errors="errors"
                    text-enable="Set in Advance"
                    text-disable="Set at Runtime"
                    :workflow-building-mode="true"
                    @onChange="onChange" />
            </div>

            <div v-if="stepOutputs.length" class="mt-2 mb-4">
                <Heading h2 separator bold size="sm"> Additional Options </Heading>

                <FormSection
                    :id="stepId"
                    :key="formKey"
                    :node-inputs="stepInputs"
                    :node-outputs="stepOutputs"
                    :step="step"
                    :datatypes="props.dataTypes"
                    :post-job-actions="postJobActions"
                    @onChange="onChangePostJobActions" />
            </div>
        </template>
    </ToolCard>
</template>
