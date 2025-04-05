import { type Ref, ref, watch } from "vue";

export function useAccessibleHover(
    elementRef: Ref<HTMLElement | null>,
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
        () => elementRef.value,
        () => {
            if (previousElement) {
                exit();
                previousElement.removeEventListener("mouseenter", enter);
                previousElement.removeEventListener("focus", enter);
                previousElement.removeEventListener("mouseleave", exit);
                previousElement.removeEventListener("blur", exit);
                previousElement.removeEventListener("keydown", keydown);
            }

            if (elementRef.value) {
                elementRef.value.addEventListener("mouseenter", enter);
                elementRef.value.addEventListener("focus", enter);
                elementRef.value.addEventListener("mouseleave", exit);
                elementRef.value.addEventListener("blur", exit);
                elementRef.value.addEventListener("keydown", keydown);
            }

            previousElement = elementRef.value;
        },
        {
            immediate: true,
        }
    );

    return isHovering;
}
