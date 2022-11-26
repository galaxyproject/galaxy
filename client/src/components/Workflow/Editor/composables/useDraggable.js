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
            x: e.pageX - rect.left,
            y: e.pageY - rect.top,
        };
        if (options.onStart?.(pos, e) === false) {
            return;
        }
        pressedDelta.value = pos;
        handleEvent(e);
    };
    const move = (e) => {
        if (!filterEvent(e)) {
            return;
        }
        if (!pressedDelta.value) {
            return;
        }
        position.value = {
            x: e.pageX - pressedDelta.value.x,
            y: e.pageY - pressedDelta.value.y,
        };
        options.onMove?.(position.value, e);
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
    };

    if (isClient) {
        const useCapture = options.useCapture ?? true;
        useEventListener(draggingHandle, "dragstart", start, useCapture);
        useEventListener(draggingHandle, "pointerdown", start, useCapture);
        useEventListener(draggingElement, "drag", move, useCapture);
        useEventListener(draggingElement, "pointermove", move, useCapture);
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
