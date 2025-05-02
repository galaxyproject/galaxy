<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { watchImmediate } from "@vueuse/core";
import { faXmark } from "font-awesome-6";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import { type ComponentSize, type ComponentSizeClassList, prefix } from "@/components/BaseComponents/componentVariants";

import GButton from "@/components/BaseComponents/GButton.vue";
import Heading from "@/components/Common/Heading.vue";

const props = defineProps<{
    show?: boolean;
    size?: ComponentSize;
    confirm?: boolean;
    footer?: boolean;
    title?: string;
}>();

const emit = defineEmits<{
    (e: "update:show", show: boolean): void;
    (e: "open"): void;
    (e: "close"): void;
    (e: "ok"): void;
    (e: "cancel"): void;
}>();

const sizeClass = computed(() => {
    const classObject: ComponentSizeClassList = {};
    classObject[prefix(props.size ?? "medium")] = true;
    return classObject;
});

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

let isOk = false;

function hideModal(ok = false) {
    isOk = ok;
    dialog.value?.close();
}

function onClickDialog(event: MouseEvent) {
    if ((event.target as HTMLElement | null)?.tagName === "DIALOG") {
        const rect = dialog.value?.getBoundingClientRect();
        const insideDialogX = rect && event.clientX >= rect.left && event.clientX <= rect.right;
        const insideDialogY = rect && event.clientY >= rect.top && event.clientY <= rect.bottom;
        const insideDialog = insideDialogX && insideDialogY;

        if (!insideDialog) {
            hideModal(false);
        }
    }
}

function onOpen() {
    emit("update:show", true);
    emit("open");

    isOk = false;
}

function onClose() {
    emit("update:show", false);
    emit("close");

    if (props.confirm && isOk) {
        emit("ok");
    } else {
        emit("cancel");
    }
}

defineExpose({ showModal, hideModal });
</script>

<template>
    <!-- This is a convenience shortcut for mouse-users to close the dialog, so disabling this warning is fine here -->
    <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions, vuejs-accessibility/click-events-have-key-events -->
    <dialog ref="dialog" class="g-dialog" :class="sizeClass" @click="onClickDialog">
        <header>
            <Heading v-if="props.title" h2 size="md"> {{ Heading }} </Heading>
            <slot name="header"></slot>
            <GButton icon-only inline class="g-modal-close-button" size="large" transparent @click="hideModal(false)">
                <FontAwesomeIcon :icon="faXmark" />
            </GButton>
        </header>

        <slot></slot>

        <footer v-if="props.footer || props.confirm">
            <slot name="footer"></slot>
            <div v-if="props.confirm" class="g-modal-confirm-buttons">
                <GButton @click="hideModal(false)"> Cancel </GButton>
                <GButton color="blue" @click="hideModal(true)"> Ok </GButton>
            </div>
        </footer>
    </dialog>
</template>

<style lang="scss" scoped>
.g-dialog {
    background-color: var(--background-color);
    border-radius: var(--spacing-2);
    border: none;

    &::backdrop {
        background-color: var(--color-blue-800);
        opacity: 0.2;
    }

    &.g-small {
        width: 600px;
    }

    &.g-medium {
        width: 900px;
    }

    &.g-large {
        width: 1200px;
    }

    header {
        display: flex;
        justify-content: flex-end;
    }
}
</style>
