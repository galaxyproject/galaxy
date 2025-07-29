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

        <Heading h3 size="sm"> Inputs </Heading>
        <Heading h3 size="sm"> Outputs </Heading>
        <Heading h3 size="sm"> Steps </Heading>
    </GModal>
</template>

<style lang="scss" scoped></style>
