<script setup lang="ts">
/**
 * Popup modal component. Offers a main slot, a heading slot, and a footer slot.
 */

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { watchImmediate } from "@vueuse/core";
import { faXmark } from "font-awesome-6";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import { type ComponentSize, type ComponentSizeClassList, prefix } from "@/components/BaseComponents/componentVariants";
import { match } from "@/utils/utils";

import GButton from "@/components/BaseComponents/GButton.vue";
import Heading from "@/components/Common/Heading.vue";

const props = defineProps<{
    /** Controls if the modal is showing. Syncable */
    show?: boolean;
    /** Controls the modals size. If unset, size can be controlled via css `width` and `height` */
    size?: ComponentSize;
    /** Shows confirm an cancel buttons in the footer, and sends out `ok` and `cancel` events */
    confirm?: boolean;
    /** Custom text for the Ok confirm button */
    okText?: string;
    /** Custom text for the Cancel confirm button */
    cancelText?: string;
    /** Renders the footer region, even if confirm is disabled */
    footer?: boolean;
    /** Text to display in the title */
    title?: string;
    /** Fixes the height of the modal to a pre-set height based on `size` */
    fixedHeight?: boolean;
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

    if (props.size) {
        classObject[prefix(props.size)] = true;
    }

    return { ...classObject, "g-fixed-height": props.fixedHeight };
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

const headingSize = computed(() =>
    match(props.size ?? "medium", {
        small: () => "sm" as const,
        medium: () => "md" as const,
        large: () => "lg" as const,
    })
);

defineExpose({ showModal, hideModal });
</script>

<template>
    <!-- This is a convenience shortcut for mouse-users to close the dialog, so disabling this warning is fine here -->
    <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions, vuejs-accessibility/click-events-have-key-events -->
    <dialog ref="dialog" class="g-dialog" :class="sizeClass" @click="onClickDialog">
        <section>
            <header>
                <Heading
                    v-if="props.title"
                    h2
                    :separator="props.size === 'large'"
                    :size="headingSize"
                    class="g-modal-title mb-0"
                    :class="props.size === 'large' ? '' : 'ml-2'">
                    {{ props.title }}
                </Heading>

                <slot name="header"></slot>

                <GButton icon-only class="g-modal-close-button" transparent size="large" @click="hideModal(false)">
                    <FontAwesomeIcon fixed-width :icon="faXmark" />
                </GButton>
            </header>

            <div class="g-modal-content">
                <slot></slot>
            </div>

            <footer v-if="props.footer || props.confirm">
                <div class="g-modal-footer-content">
                    <slot name="footer"></slot>
                </div>

                <div v-if="props.confirm" class="g-modal-confirm-buttons">
                    <GButton @click="hideModal(false)"> {{ props.cancelText ?? "Cancel" }} </GButton>
                    <GButton color="blue" @click="hideModal(true)"> {{ props.okText ?? "Ok" }} </GButton>
                </div>
            </footer>
        </section>
    </dialog>
</template>

<style lang="scss" scoped>
.g-dialog {
    background-color: var(--background-color);
    border-radius: var(--spacing-2);
    border: none;

    padding: var(--spacing-3);

    section {
        height: 100%;
        width: 100%;
        display: flex;
        flex-direction: column;
        gap: var(--spacing-2);

        .g-modal-content {
            flex-grow: 1;
            overflow: auto;
            max-height: 100%;
            display: flex;
            flex-direction: column;
        }
    }

    &::backdrop {
        background-color: var(--color-blue-800);
        opacity: 0.33;
    }

    &.g-small {
        width: 600px;

        &.g-fixed-height {
            height: 700px;
        }
    }

    &.g-medium {
        width: 900px;

        &.g-fixed-height {
            height: 750px;
        }
    }

    &.g-large {
        width: 1450px;

        &.g-fixed-height {
            height: 800px;
        }
    }

    header {
        display: flex;
        justify-content: flex-end;
        gap: var(--spacing-1);

        .g-modal-title {
            flex-grow: 1;
        }
    }

    footer {
        margin: calc(var(--spacing-3) * -1);
        padding: var(--spacing-3);
        border-top: 1px solid var(--color-grey-200);
        display: flex;

        .g-modal-footer-content {
            flex-grow: 1;
        }
    }
}
</style>
