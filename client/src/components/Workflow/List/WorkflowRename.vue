<script setup lang="ts">
import { BForm, BFormInput, BModal } from "bootstrap-vue";
import { ref } from "vue";

import { updateWorkflow } from "@/components/Workflow/workflows.services";
import { Toast } from "@/composables/toast";
import localize from "@/utils/localization";

import Heading from "@/components/Common/Heading.vue";

interface Props {
    id: string;
    name: string;
    show: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "close"): void;
    (e: "onRename", name: string): void;
}>();

const nameModel = ref(props.name);
const workflowNameInput = ref<HTMLInputElement | null>(null);

async function onRename(newName: string) {
    try {
        await updateWorkflow(props.id, { name: newName });
        Toast.success("工作流重命名成功");
    } catch (e) {
        Toast.error("工作流重命名失败");
    } finally {
        emit("close");
    }
}
</script>

<template>
    <BModal
        :visible="show"
        :ok-disabled="!nameModel"
        :ok-title="localize('重命名')"
        @ok="onRename(nameModel)"
        @hide="$emit('close')">
        <template v-slot:modal-title>
            <Heading h2 inline size="sm"> 重命名工作流: {{ localize(name) }}</Heading>
        </template>

        <BForm @submit.prevent="onRename(nameModel)">
            <BFormInput
                id="workflow-name-input"
                ref="workflowNameInput"
                v-model="nameModel"
                type="text"
                placeholder="输入新名称" />
        </BForm>
    </BModal>
</template>
