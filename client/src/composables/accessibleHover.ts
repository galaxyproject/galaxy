import { type MaybeRefOrGetter, toValue } from "@vueuse/core";
import { ref, watch } from "vue";

export function useAccessibleHover(
    elementRef: MaybeRefOrGetter<HTMLElement | null>,
    onHoverEnter?: () => void,
    onHoverExit?: () => void
) {
    const isHovering = ref(false);
    let previousElement: HTMLElement | null = null;

    function enter() {
        if (!isHovering.value) {
            onHoverEnter?.();
            isHovering.value = true;
        }
    }

    function exit() {
        if (isHovering.value) {
            onHoverExit?.();
            isHovering.value = false;
        }
    }

    function keydown(event: KeyboardEvent) {
        if (event.key === "Escape") {
            exit();
        }
    }

    watch(
        () => toValue(elementRef),
        (element) => {
            if (previousElement) {
                exit();
                previousElement.removeEventListener("mouseenter", enter);
                previousElement.removeEventListener("focus", enter);
                previousElement.removeEventListener("mouseleave", exit);
                previousElement.removeEventListener("blur", exit);
                previousElement.removeEventListener("keydown", keydown);
            }

            if (element) {
                element.addEventListener("mouseenter", enter);
                element.addEventListener("focus", enter);
                element.addEventListener("mouseleave", exit);
                element.addEventListener("blur", exit);
                element.addEventListener("keydown", keydown);
            }

            previousElement = element;
        },
        {
            immediate: true,
        }
    );

    return isHovering;
}
