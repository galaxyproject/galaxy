import { type MaybeRefOrGetter, resolveUnref } from "@vueuse/core";

import { useAnimationFrame } from "./animationFrame";

export type Size = { width: number; height: number };
type CallbackValue = { clientSize: Size; scrollSize: Size };
export type AnimationFrameResizeObserverCallback = (newValue: CallbackValue, oldValue: CallbackValue) => void;

export function useAnimationFrameResizeObserver(
    element: MaybeRefOrGetter<HTMLElement | null>,
    callback: AnimationFrameResizeObserverCallback
) {
    let clientSize = { width: 0, height: 0 };
    let scrollSize = { width: 0, height: 0 };

    const isSameSize = (a: Size, b: Size) => {
        return a.width === b.width && a.height === b.height;
    };

    const { stop } = useAnimationFrame(() => {
        const el = resolveUnref(element);

        if (!el) {
            return;
        }

        const newClientSize = {
            width: el.clientWidth,
            height: el.clientHeight,
        };

        const newScrollSize = {
            width: el.scrollWidth,
            height: el.scrollHeight,
        };

        if (!isSameSize(clientSize, newClientSize) || !isSameSize(scrollSize, newScrollSize)) {
            callback({ clientSize: newClientSize, scrollSize: newScrollSize }, { clientSize, scrollSize });
            clientSize = newClientSize;
            scrollSize = newScrollSize;
        }
    });

    return { stop };
}
