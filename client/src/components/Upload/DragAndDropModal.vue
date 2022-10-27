<script setup>
import { useEventListener } from "@vueuse/core";
import { ref, computed } from "vue";

/** prevents any internal drag-events from opening the modal */
const dragBlocked = ref(false);

const isDragOver = ref(false);

const modal = ref(null);

useEventListener(
    document.body,
    "dragstart",
    (event) => {
        dragBlocked.value = true;
    },
    true
);

useEventListener(
    document.body,
    "dragover",
    (event) => {
        if (!dragBlocked.value) {
            // prevent the browser from opening the file
            event.preventDefault();
        }
    },
    true
);

useEventListener(document.body, "drop", (event) => {
    if (!dragBlocked.value) {
        // prevent the browser from opening the file
        event.preventDefault();
        modal.value.hide();
    }
}),
    true;

useEventListener(
    document.body,
    "dragend",
    (event) => {
        dragBlocked.value = false;
        isDragOver.value = false;
        modal.value.hide();
    },
    true
);

useEventListener(
    document.body,
    "dragenter",
    (event) => {
        if (!dragBlocked.value && !isAnyModalOpen()) {
            isDragOver.value = false;
            modal.value.show();
            event.preventDefault();
        }
    },
    true
);

function isAnyModalOpen() {
    return document.querySelectorAll(".modal.show").length > 0;
}

const modalContentElement = ref(null);
const modalClass = computed(() => {
    if (isDragOver.value) {
        return "ui-drag-and-drop-modal drag-over";
    } else {
        return "ui-drag-and-drop-modal";
    }
});

useEventListener(modalContentElement, "dragenter", () => {
    isDragOver.value = true;
});

useEventListener(modalContentElement, "dragleave", () => {
    isDragOver.value = false;
});
</script>

<template>
    <b-modal ref="modal" :modal-class="modalClass" hide-header hide-footer centered>
        <div ref="modalContentElement" class="inner-content h-xl">Drop Files here to Upload them</div>
    </b-modal>
</template>

<style lang="scss">
@import "theme/blue.scss";

.ui-drag-and-drop-modal {
    .modal-content {
        background-color: transparent;
        border-radius: 16px;
        border: 6px dashed;
        border-color: $brand-secondary;
        min-height: 40vh;

        .modal-body {
            display: flex;
        }

        .inner-content {
            flex: 1 1 auto;
            display: grid;
            place-items: center;
            color: $brand-secondary;
            font-weight: bold;
        }
    }

    &.drag-over {
        .modal-content {
            border-color: $brand-success;

            .inner-content {
                color: $brand-success;
            }
        }
    }
}
</style>
