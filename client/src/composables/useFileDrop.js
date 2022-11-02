import { ref, unref } from "vue";
import { useEventListener } from "@vueuse/core";

/**
 * Custom File-Drop composable
 * @param dropZone Element which files should be dropped on
 * @param onDrop callback function called when drop occurs
 * @param solo when true, only reacts if no modal is open
 */
export function useFileDrop(dropZone, onDrop, solo) {
    const isFileOverDocument = ref(false);
    const isFileOverDropZone = ref(false);

    const dragBlocked = ref(false);

    // Don't react to page-internal drag events
    useEventListener(
        document.body,
        "dragstart",
        () => {
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

    useEventListener(
        document.body,
        "drop",
        (event) => {
            if (!dragBlocked.value) {
                // prevent the browser from opening the file
                event.preventDefault();

                isFileOverDocument.value = false;
                unref(onDrop)(event);
            }
            dragBlocked.value = false;
        },
        true
    );

    useEventListener(
        document.body,
        "dragend",
        () => {
            // reset on drag end
            isFileOverDocument.value = false;
            isFileOverDropZone.value = false;
            dragBlocked.value = false;
        },
        true
    );

    useEventListener(
        document.body,
        "dragenter",
        (event) => {
            // init values if drag is possible
            if (!dragBlocked.value && !(unref(solo) && isAnyModalOpen())) {
                isFileOverDocument.value = true;
                isFileOverDropZone.value = false;

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
        },
        true
    );

    useEventListener(
        dropZone,
        "dragleave",
        () => {
            isFileOverDropZone.value = false;
        },
        true
    );

    return { isFileOverDocument, isFileOverDropZone };
}
