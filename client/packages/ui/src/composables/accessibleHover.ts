import { type MaybeRefOrGetter, toValue } from "@vueuse/core";
import { ref, watch } from "vue";

import { DEFAULT_TOOLTIP_HOVER_DELAY_MS, useDelayedAction } from "../utils/tooltipTiming";

interface AccessibleHoverOptions {
    showDelayMs?: number;
    delayFocusEnter?: boolean;
}

export function useAccessibleHover(
    elementRef: MaybeRefOrGetter<HTMLElement | null>,
    onHoverEnter?: () => void,
    onHoverExit?: () => void,
    options?: AccessibleHoverOptions,
) {
    const isHovering = ref(false);
    let previousElement: HTMLElement | null = null;
    const enterDelay = useDelayedAction(options?.showDelayMs ?? DEFAULT_TOOLTIP_HOVER_DELAY_MS);
    const focusHandler = options?.delayFocusEnter ? enterWithDelay : enter;

    function enter() {
        enterDelay.clear();
        if (!isHovering.value) {
            onHoverEnter?.();
            isHovering.value = true;
        }
    }

    function enterWithDelay() {
        if (isHovering.value || enterDelay.isScheduled()) {
            return;
        }
        enterDelay.schedule(() => enter());
    }

    function exit() {
        enterDelay.clear();
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
                previousElement.removeEventListener("mouseenter", enterWithDelay);
                previousElement.removeEventListener("focus", focusHandler);
                previousElement.removeEventListener("mouseleave", exit);
                previousElement.removeEventListener("blur", exit);
                previousElement.removeEventListener("keydown", keydown);
            }

            if (element) {
                element.addEventListener("mouseenter", enterWithDelay);
                element.addEventListener("focus", focusHandler);
                element.addEventListener("mouseleave", exit);
                element.addEventListener("blur", exit);
                element.addEventListener("keydown", keydown);
            }

            previousElement = element;
        },
        {
            immediate: true,
        },
    );

    return isHovering;
}
