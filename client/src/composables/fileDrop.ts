import { ref, unref, type Ref } from "vue";
import { useEventListener, type MaybeComputedRef } from "@vueuse/core";
import { wait } from "@/utils/wait";

export type FileDropHandler = (event: DragEvent) => void;

/**
 * Custom File-Drop composable
 * @param dropZone Element which files should be dropped on
 * @param onDrop callback function called when drop occurs
 * @param solo when true, only reacts if no modal is open
 */
export function useFileDrop(
    dropZone: MaybeComputedRef<EventTarget | null | undefined>,
    onDrop: Ref<FileDropHandler> | FileDropHandler,
    solo: MaybeComputedRef<boolean>
) {
    const isFileOverDocument = ref(false);
    const isFileOverDropZone = ref(false);

    // blocks drag events in this composable, to avoid drag events in unwanted situations
    let dragBlocked = false;

    // keeps track if the drag has exited, to avoid premature drag canceling
    let hasExited = true;

    // Don't react to page-internal drag events
    useEventListener(
        document.body,
        "dragstart",
        () => {
            dragBlocked = true;
        },
        true
    );

    useEventListener(
        document.body,
        "dragover",
        (event) => {
            if (!dragBlocked) {
                // prevent the browser from opening the file
                event.preventDefault();
                hasExited = false;
            }
        },
        true
    );

    useEventListener(
        document.body,
        "drop",
        (event) => {
            if (!dragBlocked) {
                // prevent the browser from opening the file
                event.preventDefault();

                if (isFileOverDropZone.value && isFileOverDocument.value) {
                    const dropHandler = unref(onDrop);
                    dropHandler(event as DragEvent);
                }
            }
            isFileOverDocument.value = false;
            dragBlocked = false;
            hasExited = true;
        },
        true
    );

    /** Reset all variables */
    const reset = (continueBlock = false) => {
        isFileOverDocument.value = false;
        isFileOverDropZone.value = false;
        if (!continueBlock) {
            dragBlocked = false;
        }
        hasExited = true;
    };

    useEventListener(document.body, "dragend", reset, true);

    useEventListener(document.body, "dragleave", async () => {
        hasExited = true;

        // This event may have been triggered by components
        // which have not been properly childed to the body yet.
        // Wait a bit, and check if hasExited is still true.
        await wait(100);

        if (hasExited) {
            reset(dragBlocked);
        }
    });

    useEventListener(
        document.body,
        "dragenter",
        (event) => {
            // init values if drag is possible
            if (!dragBlocked && !(unref(solo) && isAnyModalOpen())) {
                isFileOverDocument.value = true;
                isFileOverDropZone.value = false;
                hasExited = false;

                event.preventDefault();
            }
        },
        true
    );

    /** returns if any bootstrap modal is open */
    function isAnyModalOpen() {
        return document.querySelectorAll(".modal.show").length > 0;
    }

    useEventListener(
        dropZone,
        "dragenter",
        () => {
            isFileOverDropZone.value = true;
            hasExited = false;
        },
        true
    );

    useEventListener(
        dropZone,
        "dragleave",
        () => {
            isFileOverDropZone.value = false;
            hasExited = false;
        },
        true
    );

    return { isFileOverDocument, isFileOverDropZone };
}
