import { createPopper, type Placement } from "@popperjs/core";
import { onMounted, onUnmounted, type Ref, ref, watch } from "vue";

export type Trigger = "click" | "hover" | "manual";

const defaultTrigger: Trigger = "hover";

export function usePopperjs(
    reference: Ref<HTMLElement>,
    popper: Ref<HTMLElement>,
    options: {
        placement: Placement | undefined;
        trigger: Trigger | undefined;
    }
) {
    const instance = ref<ReturnType<typeof createPopper>>();
    const visible = ref(false);
    const listeners : any = [];

    const doOpen = () => (visible.value = true);
    const doClose = () => (visible.value = false);
    const doCloseForDocument = (e: Event) => {
        if (!reference.value?.contains(e.target as Element) && !popper.value?.contains(e.target as Element)) {
            visible.value = false;
        }
    };

    function addEventListener(target: any, event: string, handler: any) {
        target.addEventListener(event, handler);
        listeners.push({ target, event, handler });
    }

    onMounted(() => {
        // create instance
        instance.value = createPopper(reference.value, popper.value!, {
            placement: options?.placement ?? "bottom",
            strategy: "absolute",
        });

        // attach event handlers
        switch (options?.trigger ?? defaultTrigger) {
            case "click": {
                addEventListener(reference.value, "click", doOpen);
                addEventListener(document, "click", doCloseForDocument);
                break;
            }

            case "hover": {
                addEventListener(reference.value, "mousedown", doClose);
                addEventListener(reference.value, "mouseout", doClose);
                addEventListener(reference.value, "mouseover", doOpen);
                break;
            }

            case "manual": {
                break;
            }

            default: {
                throw TypeError();
            }
        }
    });

    onUnmounted(() => {
        // destroy instance
        instance.value?.destroy();
        instance.value = undefined;

        // remove event handlers
        listeners.forEach((l: any) => {
            l.target.removeEventListener(l.event, l.handler);
        });
        listeners.length = 0;
    });

    watch(
        () => [instance.value, visible.value],
        () => {
            instance.value?.update();
        }
    );

    return {
        instance,
        visible,
    };
}
