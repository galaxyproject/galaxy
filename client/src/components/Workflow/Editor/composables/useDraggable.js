import { computed, ref } from "vue-demi";
import { isClient, resolveUnref, toRefs } from "@vueuse/shared";
import { useEventListener } from "@vueuse/core";

/**
 * Make elements draggable.
 *
 * @see https://vueuse.org/useDraggable
 * @param target
 * @param options
 */
export function useDraggable(target, options = {}) {
    const draggingElement = options.draggingElement ?? window;
    const draggingHandle = options.handle ?? target;
    const position = ref(resolveUnref(options.initialValue) ?? { x: 0, y: 0 });
    const pressedDelta = ref();
    const cleanUpPointerMove = ref();
    const cleanUpDragMove = ref();

    const filterEvent = (e) => {
        if (options.pointerTypes) {
            return options.pointerTypes.includes(e.pointerType);
        }
        return true;
    };

    const handleEvent = (e) => {
        if (resolveUnref(options.preventDefault)) {
            e.preventDefault();
        }
        if (resolveUnref(options.stopPropagation)) {
            e.stopPropagation();
        }
    };

    const start = (e) => {
        if (!filterEvent(e)) {
            return;
        }
        if (resolveUnref(options.exact) && e.target !== resolveUnref(target)) {
            return;
        }
        const rect = resolveUnref(target)?.getBoundingClientRect();
        const pos = {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top,
        };
        if (options.onStart?.(pos, e) === false) {
            return;
        }
        pressedDelta.value = pos;
        // define move inline because the event lister scope never receives updates to the initial pressedDelta value
        // (interestingly not a problem if using move directly)
        const move = (e) => {
            if (!filterEvent(e)) {
                return;
            }
            if (!pressedDelta.value) {
                return;
            }
            position.value = {
                x: e.clientX - pressedDelta.value.x,
                y: e.clientY - pressedDelta.value.y,
            };
            options.onMove?.(position.value, e);
            handleEvent(e);
        };
        function throttleMove(e) {
            return throttledWrite(() => move(e));
        }

        cleanUpPointerMove.value && cleanUpPointerMove.value();
        cleanUpDragMove.value && cleanUpDragMove.value();
        cleanUpDragMove.value = useEventListener(window, "dragover", throttleMove, options.useCapture ?? true);
        cleanUpPointerMove.value = useEventListener(
            draggingElement,
            "pointermove",
            throttleMove,
            options.useCapture ?? true
        );
        handleEvent(e);
    };
    const end = (e) => {
        if (!filterEvent(e)) {
            return;
        }
        if (!pressedDelta.value) {
            return;
        }
        pressedDelta.value = undefined;
        options.onEnd?.(position.value, e);
        handleEvent(e);
        cleanUpPointerMove.value && cleanUpPointerMove.value();
        cleanUpDragMove.value && cleanUpDragMove.value();
    };

    if (isClient) {
        const useCapture = options.useCapture ?? true;
        useEventListener(draggingHandle, "dragstart", start, useCapture);
        useEventListener(draggingHandle, "pointerdown", start, useCapture);
        useEventListener(draggingElement, "dragend", end, useCapture);
        useEventListener(draggingElement, "pointerup", end, useCapture);
    }

    return {
        ...toRefs(position),
        position,
        isDragging: computed(() => !!pressedDelta.value),
        style: computed(() => `left:${position.value.x}px;top:${position.value.y}px;`),
    };
}

function throttle(timer) {
    let queuedCallback;
    return (callback) => {
        if (!queuedCallback) {
            timer(() => {
                const cb = queuedCallback;
                queuedCallback = null;
                cb();
            });
        }
        queuedCallback = callback;
    };
}

const throttledWrite = throttle(requestAnimationFrame);
