import { createPopper, type Placement } from "@popperjs/core";
import { onMounted, onUnmounted, type Ref, ref, watch } from "vue";

import {
    DEFAULT_TOOLTIP_HOVER_DELAY_MS,
    INTERACTIVE_POPOVER_CLOSE_DELAY_MS,
    useDelayedAction,
} from "@/utils/tooltipTiming";

export type Trigger = "click" | "hover" | "none";

const defaultTrigger: Trigger = "hover";

export function usePopper(
    reference: Ref<HTMLElement>,
    popper: Ref<HTMLElement>,
    options: { interactive?: boolean; placement?: Placement; trigger?: Trigger; hoverDelay?: number },
) {
    const instance = ref<ReturnType<typeof createPopper>>();
    const visible = ref(false);
    const listeners: Array<{ target: EventTarget; event: string; handler: EventListener }> = [];

    const openDelay = useDelayedAction(options.hoverDelay ?? DEFAULT_TOOLTIP_HOVER_DELAY_MS);
    const closeDelay = useDelayedAction(options.interactive ? INTERACTIVE_POPOVER_CLOSE_DELAY_MS : 0);

    const doOpenImmediately = () => {
        openDelay.clear();
        closeDelay.clear();
        visible.value = true;
    };
    const doOpen = () => {
        closeDelay.clear();
        if (visible.value || openDelay.isScheduled()) {
            return;
        }
        openDelay.schedule(() => {
            visible.value = true;
        });
    };
    const doClose = () => {
        openDelay.clear();
        closeDelay.schedule(() => {
            visible.value = false;
        });
    };
    const doCloseDocument = (e: Event) => {
        if (!reference.value?.contains(e.target as Node) && !popper.value?.contains(e.target as Node)) {
            openDelay.clear();
            closeDelay.clear();
            visible.value = false;
        }
    };
    const doCloseElement = (event: Event) => {
        const target = event.target as Element;
        if (target && target.closest(".popper-close")) {
            openDelay.clear();
            closeDelay.clear();
            visible.value = false;
        }
    };
    const doCloseEscape = (event: Event) => {
        const keyboardEvent = event as KeyboardEvent;
        if (keyboardEvent.key === "Escape") {
            openDelay.clear();
            closeDelay.clear();
            visible.value = false;
        }
    };

    const addEventListener = (target: EventTarget, event: string, handler: EventListener) => {
        target.addEventListener(event, handler);
        listeners.push({ target, event, handler });
    };

    onMounted(() => {
        instance.value = createPopper(reference.value, popper.value, {
            placement: options.placement ?? "bottom",
            strategy: "absolute",
            modifiers: [
                {
                    name: "offset",
                    options: {
                        offset: [0, 5],
                    },
                },
            ],
        });

        const trigger = options.trigger ?? defaultTrigger;
        if (trigger === "click") {
            addEventListener(reference.value, "click", doOpenImmediately);
            addEventListener(popper.value, "click", doCloseElement);
            addEventListener(document, "click", doCloseDocument);
            addEventListener(document, "keydown", doCloseEscape);
        } else if (trigger === "hover") {
            addEventListener(reference.value, "mouseover", doOpen);
            addEventListener(reference.value, "mouseout", doClose);
            addEventListener(popper.value, "mouseover", doOpen);
            addEventListener(popper.value, "mouseout", doClose);
        }
    });

    onUnmounted(() => {
        openDelay.clear();
        closeDelay.clear();
        instance.value?.destroy();
        listeners.forEach(({ target, event, handler }) => target.removeEventListener(event, handler));
        listeners.length = 0;
    });

    watch([instance, visible], () => instance.value?.update());

    return { instance, visible };
}
