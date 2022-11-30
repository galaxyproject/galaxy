import { useAnimationFrame } from "./animationFrame";
import { unref } from "vue";

export function useAnimationFrameResizeObserver(element, callback) {
    var lastSize = { width: 0, height: 0 };

    const { stop } = useAnimationFrame(() => {
        const el = unref(element);
        const width = el.offsetWidth;
        const height = el.offsetHeight;

        if (lastSize.width !== width || lastSize.height !== height) {
            callback({ width, height }, lastSize);
            lastSize = { width, height };
        }
    });

    return { stop };
}
