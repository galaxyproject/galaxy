import { type MaybeRefOrGetter, useEventListener } from "@vueuse/core";
import { computed, type Ref, ref, unref } from "vue";

export type FileDropHandler = (event: DragEvent) => void;

/**
 * Custom File-Drop composable
 * @param dropZone Element which files should be dropped on
 * @param onDrop callback function called when drop occurs
 * @param onDropCancel callback function called when drop cancelled
 * @param solo when true, only reacts if no modal is open
 * @param idleTime how long to wait until state resets
 */
export function useFileDrop(
    dropZone: MaybeRefOrGetter<EventTarget | null | undefined>,
    onDrop: Ref<FileDropHandler> | FileDropHandler,
    onDropCancel: Ref<FileDropHandler> | FileDropHandler,
    solo: MaybeRefOrGetter<boolean>,
    idleTime = 800
) {
    /** returns if any bootstrap modal or workflow run form is open */
    function isAnyModalOpen() {
        return (
            document.querySelectorAll(".modal.show").length > 0 ||
            document.querySelectorAll(".workflow-run-form-simple").length > 0
        );
    }

    type State = "idle" | "blocked" | "fileDragging";
    type StateMachine = {
        [_state in State]: (event: MouseEvent) => State;
    };

    const currentState: Ref<State> = ref("idle");

    let idleTimer: ReturnType<typeof setTimeout> | null = null;
    const resetTimer = () => {
        if (idleTimer) {
            clearTimeout(idleTimer);
        }
    };

    const stateMachine = {
        idle(event: MouseEvent): State {
            switch (event.type) {
                case "dragstart":
                    return "blocked";
                case "dragenter":
                    if (!(unref(solo) && isAnyModalOpen())) {
                        return "fileDragging";
                    }
                    break;
            }

            return "idle";
        },
        blocked(event: MouseEvent): State {
            switch (event.type) {
                case "drop":
                    return "idle";
                case "dragend":
                    return "idle";
            }

            return "blocked";
        },
        fileDragging(event: MouseEvent): State {
            resetTimer();

            switch (event.type) {
                case "dragover":
                    event.preventDefault();
                    idleTimer = setTimeout(() => (currentState.value = "idle"), idleTime);
                    break;
                case "drop":
                    event.preventDefault();
                    if (isFileOverDropZone.value) {
                        const dropHandler = unref(onDrop);
                        dropHandler(event as DragEvent);
                    } else {
                        const dropCancelHandler = unref(onDropCancel);
                        dropCancelHandler(event as DragEvent);
                    }
                    return "idle";
                case "dragend":
                    return "idle";
            }

            return "fileDragging";
        },
    } as const satisfies StateMachine;

    const eventHandler = (event: MouseEvent) => (currentState.value = stateMachine[currentState.value](event));

    useEventListener(document.body, "dragstart", eventHandler, true);
    useEventListener(document.body, "dragover", eventHandler, true);
    useEventListener(document.body, "drop", eventHandler, true);
    useEventListener(document.body, "dragend", eventHandler, true);
    useEventListener(document.body, "dragenter", eventHandler, true);

    const isFileOverDocument = computed({
        get() {
            return currentState.value === "fileDragging";
        },
        set(value) {
            if (value !== true) {
                currentState.value = "idle";
            } else {
                currentState.value = "fileDragging";
            }
        },
    });

    const isFileOverDropZone = ref(false);

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
