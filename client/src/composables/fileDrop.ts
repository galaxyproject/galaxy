import { type MaybeRefOrGetter, useEventListener } from "@vueuse/core";
import { computed, type Ref, ref, unref } from "vue";

export type FileDropHandler = (event: DragEvent) => void;

export interface FileDropOptions {
    /** Element which files should be dropped on. */
    dropZone: MaybeRefOrGetter<EventTarget | null | undefined>;
    /** Callback function called when drop occurs. */
    onDrop: Ref<FileDropHandler> | FileDropHandler;
    /** Callback function called when drop cancelled. */
    onDropCancel: Ref<FileDropHandler> | FileDropHandler;
    /** When true, only reacts if no modal is open. */
    solo: MaybeRefOrGetter<boolean>;
    /** How long to wait until state resets (ms). By default, 800ms. */
    idleTime?: number;
    /** When true, dragging over child elements keeps isFileOverDropZone true. Default is false. */
    ignoreChildrenOnLeave?: boolean;
}

/**
 * Custom File-Drop composable
 * @param options configuration for file-drop handling
 */
export function useFileDrop({
    dropZone,
    onDrop,
    onDropCancel,
    solo,
    idleTime = 800,
    ignoreChildrenOnLeave = false,
}: FileDropOptions) {
    /** returns true if any other more specific file drop target is on the screen and should
     *  supersede the global file drop or if an existing modal is present and should likewise
     *  take precedent.
     */
    function disableGlobalDropTargetTarget() {
        return (
            document.querySelectorAll(".modal.show").length > 0 ||
            document.querySelectorAll("[data-galaxy-file-drop-target]").length > 0
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
                    if (!(unref(solo) && disableGlobalDropTargetTarget())) {
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
                    idleTimer = setTimeout(() => {
                        currentState.value = "idle";
                        isFileOverDropZone.value = false;
                    }, idleTime);
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
        true,
    );

    useEventListener(
        dropZone,
        "dragleave",
        (event: DragEvent) => {
            if (ignoreChildrenOnLeave) {
                if (isDragLeaveToChild(dropZone, event)) {
                    return;
                }
            }

            isFileOverDropZone.value = false;
        },
        true,
    );

    useEventListener(
        dropZone,
        "drop",
        () => {
            isFileOverDropZone.value = false;
        },
        true,
    );

    return { isFileOverDocument, isFileOverDropZone };
}

/**
 * Returns true when a dragleave event moves into a descendant, meaning the drop zone is still active.
 */
function isDragLeaveToChild(dropZone: MaybeRefOrGetter<EventTarget | null | undefined>, event: DragEvent) {
    const target = unref(dropZone) as HTMLElement | null;
    const relatedTarget = event.relatedTarget as Node | null;

    return Boolean(target && relatedTarget && target.contains(relatedTarget));
}
