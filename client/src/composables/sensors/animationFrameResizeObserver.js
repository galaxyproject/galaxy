import { useAnimationFrame } from "./animationFrame";
import { unref } from "vue";

export function useAnimationFrameResizeObserver(element, callback) {
    var clientSize = { width: 0, height: 0 };
    var scrollSize = { width: 0, height: 0 };

    const isSameSize = (a, b) => {
        return a.width === b.width && a.height === b.height;
    };

    const { stop } = useAnimationFrame(() => {
        const el = unref(element);

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
