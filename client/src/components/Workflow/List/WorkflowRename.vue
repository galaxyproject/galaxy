<script setup lang="ts">
import { computed, ref } from "vue";

import { updateWorkflow } from "@/components/Workflow/workflows.services";
import { Toast } from "@/composables/toast";
import localize from "@/utils/localization";

import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    id: string;
    name: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "close"): void;
}>();

const nameModel = ref(props.name);
const renaming = ref(false);

const nameRemainsSame = computed(() => nameModel.value.trim() === props.name.trim());

async function onRename(newName: string) {
    if (nameRemainsSame.value || renaming.value) {
        return;
    }

    try {
        renaming.value = true;
        await updateWorkflow(props.id, { name: newName.trim() });
        Toast.success("Workflow renamed");
    } catch (e) {
        Toast.error("Failed to rename workflow");
    } finally {
        renaming.value = false;
        emit("close");
    }
}
</script>

<template>
    <GModal
        show
        :ok-text="localize('Rename')"
        :ok-disabled="nameRemainsSame || renaming"
        :title="`Rename workflow: ${props.name}`"
        confirm
        @ok="onRename(nameModel)"
        @close="emit('close')"
        @cancel="emit('close')">
        <GFormInput
            id="workflow-name-input"
            v-model="nameModel"
            class="w-100"
            :disabled="renaming"
            type="text"
            placeholder="Enter new name"
            @keydown.enter.prevent="onRename(nameModel)" />

        <template v-slot:footer>
            <LoadingSpan v-if="renaming" :message="localize('Renaming workflow')" />
        </template>
    </GModal>
</template>
