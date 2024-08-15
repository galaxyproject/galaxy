import { type MaybeRefOrGetter, resolveUnref } from "@vueuse/core";
import { reactive, ref } from "vue";

import { useAnimationFrame } from "./animationFrame";

export function useAnimationFrameScroll(element: MaybeRefOrGetter<HTMLElement | null>) {
    const scrollLeft = ref(0);
    const scrollTop = ref(0);

    const arrived = reactive({
        left: true,
        right: false,
        top: true,
        bottom: false,
    });

    const { stop } = useAnimationFrame(() => {
        const el = resolveUnref(element);

        if (!el) {
            return;
        }

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
