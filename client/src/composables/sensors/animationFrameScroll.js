import { useAnimationFrame } from "./animationFrame";
import { reactive, ref, unref } from "vue";

export function useAnimationFrameScroll(element) {
    const scrollLeft = ref(0);
    const scrollTop = ref(0);

    const arrived = reactive({
        left: true,
        right: false,
        top: true,
        bottom: false,
    });

    const { stop } = useAnimationFrame(() => {
        const el = unref(element);
        const left = el.scrollLeft;

        if (left !== scrollLeft.value) {
            scrollLeft.value = left;
            arrived.left = left <= 0;
            arrived.right = left + el.clientWidth >= el.scrollWidth - 1;
        }

        const top = el.scrollTop;

        if (top !== scrollTop.value) {
            scrollTop.value = top;
            arrived.top = top <= 0;
            arrived.bottom = top + el.clientHeight >= el.scrollHeight - 1;
        }
    });

    return { scrollLeft, scrollTop, arrived, stop };
}
