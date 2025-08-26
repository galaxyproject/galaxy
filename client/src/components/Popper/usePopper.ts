import { createPopper, type Placement } from "@popperjs/core";
import { onMounted, onUnmounted, type Ref, ref, watch } from "vue";

export type Trigger = "click" | "hover" | "none";

const defaultTrigger: Trigger = "hover";

const DELAY_CLOSE = 50;

export function usePopper(
    reference: Ref<HTMLElement>,
    popper: Ref<HTMLElement>,
    options: { interactive?: boolean; placement?: Placement; trigger?: Trigger },
) {
    const instance = ref<ReturnType<typeof createPopper>>();
    const visible = ref(false);
    const listeners: Array<{ target: EventTarget; event: string; handler: EventListener }> = [];

    let closeHandler: ReturnType<typeof setTimeout> | undefined;

    const doOpen = () => {
        closeHandler && clearTimeout(closeHandler);
        visible.value = true;
    };
    const doClose = () => {
        const delay = options.interactive ? DELAY_CLOSE : 0;
        closeHandler && clearTimeout(closeHandler);
        closeHandler = setTimeout(() => (visible.value = false), delay);
    };
    const doCloseDocument = (e: Event) => {
        if (!reference.value?.contains(e.target as Node) && !popper.value?.contains(e.target as Node)) {
            visible.value = false;
        }
    };
    const doCloseElement = (event: Event) => {
        const target = event.target as Element;
        if (target && target.closest(".popper-close")) {
            visible.value = false;
        }
    };
    const doCloseEscape = (event: Event) => {
        const keyboardEvent = event as KeyboardEvent;
        if (keyboardEvent.key === "Escape") {
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
            addEventListener(reference.value, "click", doOpen);
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
        instance.value?.destroy();
        listeners.forEach(({ target, event, handler }) => target.removeEventListener(event, handler));
        listeners.length = 0;
    });

    watch([instance, visible], () => instance.value?.update());

    return { instance, visible };
}
