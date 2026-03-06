<script setup lang="ts">
import { computed, ref } from "vue";

import { Toast } from "@/composables/toast";
import localize from "@/utils/localization";

import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    /**
     * The current name of the item to be renamed. This is used to initialize the input field and to determine if the name has changed.
     */
    name: string;
    /**
     * What is being renamed, used for display in the modal title and toast messages, as well as setting the input field `id`
     * @default "item"
     */
    itemType?: string;
    /**
     * The action to perform the rename. Should return a promise that resolves if the rename was successful and rejects if it failed. The new name is passed as an argument.
     */
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

/** The new name is invalid if it's the same as original or empty */
const nameInvalid = computed(() => nameModel.value.trim() === props.name.trim() || !nameModel.value.trim());

async function onRename(newName: string) {
    if (nameInvalid.value || renaming.value) {
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
        :ok-disabled="nameInvalid || renaming"
        :title="`Rename ${props.itemType}: ${props.name}`"
        confirm
        :close-on-ok="false"
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
