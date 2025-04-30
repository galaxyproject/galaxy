<script setup lang="ts">
import { watchImmediate } from "@vueuse/core";
import { onBeforeUnmount, onMounted, ref } from "vue";

const props = defineProps<{
    show?: boolean;
}>();

const emit = defineEmits<{
    (e: "update:show", show: boolean): void;
    (e: "open"): void;
    (e: "close"): void;
}>();

const dialog = ref<HTMLDialogElement | null>(null);

onMounted(() => {
    if (dialog.value) {
        dialog.value.addEventListener("close", onClose);
        dialog.value.addEventListener("open", onOpen);
    }
});

onBeforeUnmount(() => {
    if (dialog.value) {
        dialog.value.removeEventListener("close", onClose);
        dialog.value.removeEventListener("open", onOpen);
    }
});

watchImmediate(
    () => props.show,
    () => {
        if (props.show) {
            showModal();
        } else {
            hideModal();
        }
    }
);

function showModal() {
    dialog.value?.showModal();
}

function hideModal() {
    dialog.value?.close();
}

function onOpen() {
    emit("update:show", true);
    emit("open");
}

function onClose() {
    emit("update:show", false);
    emit("close");
}

defineExpose({ showModal, hideModal });
</script>

<template>
    <dialog ref="dialog" class="g-dialog">
        <slot></slot>
    </dialog>
</template>

<style lang="scss" scoped>
.g-dialog {
    background-color: var(--background-color);
    border-radius: var(--spacing-2);

    &::backdrop {
        background-color: var(--color-blue-800);
    }
}
</style>
