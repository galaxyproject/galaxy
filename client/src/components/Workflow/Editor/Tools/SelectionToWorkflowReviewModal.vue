<script setup lang="ts">
import { ref } from "vue";

import type {
    InputReconnectionMap,
    OutputReconnectionMap,
} from "@/components/Workflow/Editor/modules/convertOpenConnections";
import type { PartialWorkflow } from "@/components/Workflow/Editor/modules/extractSubworkflow";

import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GFormLabel from "@/components/BaseComponents/Form/GFormLabel.vue";
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
    (e: "renameInput", id: string, name: string): void;
    (e: "renameOutput", id: string, name: string): void;
}>();

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
            <div class="inputs">
                <Heading h3 size="sm" class="mb-0"> Inputs </Heading>

                <span> Converted from connections </span>

                <div v-for="(inputLink, label) in props.inputMap" :key="`${inputLink.id}-${inputLink.output_name}`">
                    {{ label }}
                </div>
            </div>

            <div class="outputs">
                <Heading h3 size="sm" class="mb-0"> Outputs </Heading>

                <span> Converted from connections </span>

                <div
                    v-for="outputReconnection in props.outputMap"
                    :key="`${outputReconnection.connection.id}-${outputReconnection.connection.output_name}`">
                    {{ outputReconnection.connection.output_name }}
                </div>
            </div>

            <div class="steps">
                <Heading h3 size="sm" class="mb-0"> Steps </Heading>

                <div v-for="(step, key) in props.workflow.steps" :key="key">
                    {{ step.name }}
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
</style>
