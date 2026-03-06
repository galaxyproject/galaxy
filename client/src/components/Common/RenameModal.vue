<script setup lang="ts">
import { computed, ref } from "vue";

import { Toast } from "@/composables/toast";
import localize from "@/utils/localization";

import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    name: string;
    itemType?: string;
    renameAction: (newName: string) => Promise<unknown>;
}

const props = withDefaults(defineProps<Props>(), {
    itemType: "item",
});

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
        await props.renameAction(newName.trim());
        Toast.success(`${props.itemType.charAt(0).toUpperCase() + props.itemType.slice(1)} renamed`);
    } catch (e) {
        Toast.error(`Failed to rename ${props.itemType}`);
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
        :title="`Rename ${props.itemType}: ${props.name}`"
        confirm
        @ok="onRename(nameModel)"
        @close="emit('close')"
        @cancel="emit('close')">
        <GFormInput
            :id="`${props.itemType}-name-input`"
            v-model="nameModel"
            class="w-100"
            :disabled="renaming"
            type="text"
            placeholder="Enter new name"
            @keydown.enter.prevent="onRename(nameModel)" />

        <template v-slot:footer>
            <LoadingSpan v-if="renaming" :message="localize(`Renaming ${props.itemType}`)" />
        </template>
    </GModal>
</template>
