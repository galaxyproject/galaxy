<script setup lang="ts">
import { ref, watch } from "vue";

import type { FilterFileSourcesOptions } from "@/api/remoteFiles";
import type { SelectionItem } from "@/components/SelectionDialog/selectionTypes";
import type { RemoteFileBrowserMode } from "@/composables/useRemoteFileBrowser";

import RemoteFileBrowserContent from "./RemoteFileBrowserContent.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

interface Props {
    /** Controls modal visibility. Use with `v-model:show`. */
    show: boolean;
    /** Title displayed in the modal header. */
    title?: string;
    /** Controls which entry types can be selected. */
    mode?: RemoteFileBrowserMode;
    /** Whether multiple entries can be selected simultaneously. */
    multiple?: boolean;
    /** Optional filter to restrict visible file sources. */
    filterOptions?: FilterFileSourcesOptions;
    /** Text displayed on the modal OK button. */
    okText?: string;
}

const props = withDefaults(defineProps<Props>(), {
    title: "Browse Remote Files",
    mode: "file",
    multiple: false,
    filterOptions: undefined,
    okText: "Select",
});

const emit = defineEmits<{
    /** Emitted to update the `show` binding (v-model:show). */
    (e: "update:show", show: boolean): void;
    /**
     * Emitted when the user confirms their selection.
     * Always an array; single-select mode will produce an array with one item.
     */
    (e: "select", items: SelectionItem[]): void;
    /** Emitted when the user dismisses the modal without making a selection. */
    (e: "cancel"): void;
}>();

const contentRef = ref<InstanceType<typeof RemoteFileBrowserContent> | null>(null);
const localSelectionCount = ref(0);

// Reset browser state and clear selection when the modal is opened
watch(
    () => props.show,
    (isOpen) => {
        if (isOpen) {
            localSelectionCount.value = 0;
            // Defer reset until the content component has mounted
            setTimeout(() => contentRef.value?.reset(), 0);
        }
    },
);

function onSelectionChange(count: number) {
    localSelectionCount.value = count;
}

function onOk() {
    const items = contentRef.value?.getSelectedItems() ?? [];
    emit("select", items);
    emit("update:show", false);
}

function onCancel() {
    emit("cancel");
    emit("update:show", false);
}
</script>

<template>
    <GModal
        :show="show"
        :title="title"
        size="large"
        fixed-height
        confirm
        :ok-text="okText"
        :ok-disabled="localSelectionCount === 0"
        :ok-disabled-title="localSelectionCount === 0 ? 'Select at least one item to continue' : undefined"
        @ok="onOk"
        @cancel="onCancel"
        @update:show="emit('update:show', $event)">
        <RemoteFileBrowserContent
            ref="contentRef"
            :mode="mode"
            :multiple="multiple"
            :filter-options="filterOptions"
            :ok-text="okText"
            :show-actions="false"
            @selection-change="onSelectionChange" />
    </GModal>
</template>
