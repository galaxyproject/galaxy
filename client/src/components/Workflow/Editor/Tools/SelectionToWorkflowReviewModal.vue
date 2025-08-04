<script setup lang="ts">
import { computed, ref } from "vue";

import type {
    InputReconnectionMap,
    OutputReconnectionMap,
} from "@/components/Workflow/Editor/modules/convertOpenConnections";
import type { PartialWorkflow } from "@/components/Workflow/Editor/modules/extractSubworkflow";
import { onAllInputs } from "@/components/Workflow/Editor/modules/onAllInputs";
import type { NewStep, Step } from "@/stores/workflowStepStore";
import { assertDefined } from "@/utils/assertions";

import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GFormLabel from "@/components/BaseComponents/Form/GFormLabel.vue";
import GLink from "@/components/BaseComponents/GLink.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import Heading from "@/components/Common/Heading.vue";

const props = defineProps<{
    workflow: PartialWorkflow;
    workflowName: string;
    workflowNameValid: boolean;
    inputMap: InputReconnectionMap;
    outputMap: OutputReconnectionMap;
    expandedSteps: Set<number>;
}>();

const emit = defineEmits<{
    (e: "rename", name: string): void;
    (e: "renameInput", id: number, to: string): void;
    (e: "renameOutput", id: number, name: string, to: string): void;
}>();

const connections = computed(() => {
    const connectionArray: Array<{
        from: number;
        to: number;
        inputName: string;
    }> = [];
    Object.values(props.workflow.steps).forEach((step) =>
        onAllInputs(step, (connection, name) =>
            connectionArray.push({ from: connection.id, to: step.id, inputName: name })
        )
    );

    return connectionArray;
});

const inputs = computed(() => {
    const steps = Object.values(props.workflow.steps);
    const inputSteps = steps.filter((step) =>
        (["parameter_input", "data_input", "data_collection_input"] as Array<NewStep["type"]>).includes(step.type)
    );

    const inputLabels = new Set(Object.keys(props.inputMap));

    const inputStepSummaries = inputSteps.map((step) => {
        return {
            step,
            label: step.label ?? step.name,
            connectedTo: connections.value.filter((connection) => connection.from === step.id),
            generated: step.label && inputLabels.has(step.label),
        };
    });

    return inputStepSummaries;
});

const allInputLabels = computed(() => inputs.value.map((input) => input.label));

function inputLabelValid(label: string) {
    return label.trim() !== "" && allInputLabels.value.indexOf(label) === allInputLabels.value.lastIndexOf(label);
}

const outputs = computed(() => {
    const steps = Object.values(props.workflow.steps);

    const outputLabels = new Set(props.outputMap.map((output) => output.name));

    const outputSummaries = steps.flatMap((step) => {
        if (!step.workflow_outputs || step.workflow_outputs.length === 0) {
            return [];
        }

        const outputs = step.workflow_outputs.map((output) => {
            return {
                step,
                label: output.label ?? output.output_name,
                name: output.output_name,
                generated: output.label && outputLabels.has(output.label),
            };
        });

        return outputs;
    });

    return outputSummaries;
});

const allOutputLabels = computed(() => outputs.value.map((output) => output.label));

function outputLabelValid(label: string) {
    return label.trim() !== "" && allOutputLabels.value.indexOf(label) === allOutputLabels.value.lastIndexOf(label);
}

function getOutputTypePretty(step: Step, name: string) {
    const output = step.outputs.find((output) => output.name === name);

    assertDefined(output);

    if ("collection" in output && output.collection) {
        return "collection";
    }

    if ("type" in output) {
        return output.type;
    }

    return "unknown";
}

function isStepGenerated(step: Step) {
    const input = inputs.value.find((input) => input.step.id === step.id);

    if (input && input.generated) {
        return true;
    }
}

function isStepExpanded(step: Step) {
    return props.expandedSteps.has(step.id);
}

const modal = ref<InstanceType<typeof GModal>>();

function showModal() {
    modal.value?.showModal();
}

defineExpose({
    showModal,
});
</script>

<template>
    <GModal ref="modal" title="Review extracted Sub-Workflow" confirm ok-text="Create Subworkflow">
        <p>
            A new sub-workflow will be created from the selection. Review the new workflow below and make any changes as
            required.
        </p>

        <GFormLabel
            class="mb-2"
            title="New Workflow Name"
            :state="props.workflowNameValid ? null : false"
            invalid-feedback="please provide a name">
            <GFormInput :value="props.workflowName" @input="(v) => emit('rename', v ?? '')" />
        </GFormLabel>

        <div class="workflow-info-grid">
            <div class="inputs list">
                <Heading h3 size="sm" class="mb-0"> Inputs </Heading>

                <div v-for="(input, index) in inputs" :key="index" class="box">
                    <div class="box-heading">
                        <span> Input Step {{ input.step.id + 1 }} </span>
                        <GLink
                            v-if="input.generated"
                            class="generated-notice"
                            tooltip
                            title="converted from input connections to selection">
                            generated
                        </GLink>
                    </div>

                    <GFormLabel
                        :state="inputLabelValid(input.label) ? null : false"
                        invalid-feedback="provide a unique input label">
                        <GFormInput
                            :value="input.label"
                            @input="(value) => emit('renameInput', input.step.id, value ?? '')" />
                    </GFormLabel>

                    <div>
                        Connected To:
                        <ul class="connection-list">
                            <li v-for="connection in input.connectedTo" :key="connection.to">
                                {{ connection.to + 1 }}:
                                {{
                                    props.workflow.steps[connection.to]?.label ??
                                    props.workflow.steps[connection.to]?.name
                                }}
                            </li>
                        </ul>
                    </div>
                </div>
            </div>

            <div class="outputs list">
                <Heading h3 size="sm" class="mb-0"> Outputs </Heading>

                <div v-for="(output, index) in outputs" :key="index" class="box">
                    <div class="box-heading">
                        <span> {{ getOutputTypePretty(output.step, output.name) }} output </span>
                        <GLink
                            v-if="output.generated"
                            class="generated-notice"
                            tooltip
                            title="converted from output connections from selection">
                            generated
                        </GLink>
                    </div>

                    <GFormLabel
                        :state="outputLabelValid(output.label) ? null : false"
                        invalid-feedback="provide a unique output label">
                        <GFormInput
                            :value="output.label"
                            @input="(value) => emit('renameOutput', output.step.id, output.name, value ?? '')" />
                    </GFormLabel>
                </div>
            </div>

            <div class="steps">
                <Heading h3 size="sm" class="mb-0"> Steps </Heading>

                <div class="step-grid">
                    <div v-for="(step, key) in props.workflow.steps" :key="key" class="box step">
                        {{ step.id + 1 }}: {{ step.name }}

                        <GLink
                            v-if="isStepGenerated(step)"
                            class="generated-notice"
                            tooltip
                            title="converted from input connections from selection">
                            generated
                        </GLink>

                        <GLink
                            v-if="isStepExpanded(step)"
                            class="expanded-notice"
                            tooltip
                            title="needs top be included for sub-workflow to function, despite not being part of the initial selection">
                            automatically included
                        </GLink>
                    </div>
                </div>
            </div>
        </div>
    </GModal>
</template>

<style lang="scss" scoped>
.workflow-info-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-areas:
        "i o"
        "s s";
    gap: var(--spacing-2);

    .inputs {
        grid-area: i;
    }

    .outputs {
        grid-area: o;
    }

    .steps {
        grid-area: s;
    }
}

.list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-2);
}

.step-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: var(--spacing-2);
}

.box {
    border: 1px solid var(--color-grey-400);
    border-radius: var(--spacing-2);
    padding: var(--spacing-2);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-1);

    &.step {
        flex-direction: row;
        justify-content: space-between;
    }

    &:has(.generated-notice) {
        border: 1px solid var(--color-green-500);
    }

    &:has(.expanded-notice) {
        border: 1px solid var(--color-orange-500);
    }

    .box-heading {
        display: flex;
        justify-content: space-between;
    }

    .connection-list {
        margin-bottom: 0;
        padding-left: var(--spacing-4);
    }
}
</style>
