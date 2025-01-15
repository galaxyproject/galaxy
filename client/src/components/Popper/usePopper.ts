import { createPopper, type Placement } from "@popperjs/core";
import { onMounted, onUnmounted, type Ref, ref, watch } from "vue";

export type Trigger = "click" | "hover" | "none";

const defaultTrigger: Trigger = "hover";

export function usePopper(
    reference: Ref<HTMLElement>,
    popper: Ref<HTMLElement>,
    options: { placement?: Placement; trigger?: Trigger }
) {
    const instance = ref<ReturnType<typeof createPopper>>();
    const visible = ref(false);
    const listeners: Array<{ target: EventTarget; event: string; handler: EventListener }> = [];

    const doOpen = () => (visible.value = true);
    const doClose = () => (visible.value = false);
    const doCloseForDocument = (e: Event) => {
        if (!reference.value?.contains(e.target as Node) && !popper.value?.contains(e.target as Node)) {
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
            addEventListener(document, "click", doCloseForDocument);
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
