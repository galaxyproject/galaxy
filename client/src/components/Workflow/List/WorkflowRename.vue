<script setup lang="ts">
import { BForm, BFormInput, BModal } from "bootstrap-vue";
import { computed, ref } from "vue";

import { updateWorkflow } from "@/components/Workflow/workflows.services";
import { Toast } from "@/composables/toast";
import localize from "@/utils/localization";

import Heading from "@/components/Common/Heading.vue";

interface Props {
    id: string;
    name: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "close"): void;
    (e: "onRename", name: string): void;
}>();

const nameModel = ref(props.name);

const nameRemainsSame = computed(() => nameModel.value.trim() === props.name.trim());

async function onRename(newName: string) {
    try {
        await updateWorkflow(props.id, { name: newName.trim() });
        Toast.success("Workflow renamed");
    } catch (e) {
        Toast.error("Failed to rename workflow");
    } finally {
        emit("close");
    }
}

function onClose() {
    emit("close");
}
</script>

<template>
    <BModal
        visible
        :ok-title="localize('Rename')"
        :ok-disabled="nameRemainsSame"
        @ok="onRename(nameModel)"
        @hide="onClose">
        <template v-slot:modal-title>
            <Heading h2 inline size="sm"> Rename workflow: {{ localize(name) }}</Heading>
        </template>

        <BForm @submit.prevent="onRename(nameModel)">
            <BFormInput
                id="workflow-name-input"
                ref="workflowNameInput"
                v-model="nameModel"
                type="text"
                placeholder="Enter new name" />
        </BForm>
    </BModal>
</template>
