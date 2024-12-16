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

    onMounted(() => {
        // create instance
        instance.value = createPopper(reference.value, popper.value!, {
            placement: options?.placement ?? "bottom",
            strategy: "absolute",
        });

        // attach event handlers
        switch (options?.trigger ?? defaultTrigger) {
            case "click": {
                reference.value.addEventListener("click", doOpen);
                document.addEventListener("click", doCloseForDocument);
                break;
            }

            case "hover": {
                reference.value.addEventListener("mousedown", doClose);
                reference.value.addEventListener("mouseout", doClose);
                reference.value.addEventListener("mouseover", doOpen);
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
        document.removeEventListener("click", doCloseForDocument, false);
        if (reference.value) {
            reference.value.removeEventListener("click", doOpen, false);
            reference.value.removeEventListener("mousedown", doClose, false);
            reference.value.removeEventListener("mouseout", doClose, false);
            reference.value.removeEventListener("mouseover", doOpen, false);
        }
    });

    const visible = ref(false);
    const doOpen = () => (visible.value = true);
    const doClose = () => (visible.value = false);

    const doCloseForDocument = (e: Event) => {
        if (!reference.value?.contains(e.target as Element) && !popper.value?.contains(e.target as Element)) {
            visible.value = false;
        }
    };

    watch(
        () => [instance.value, visible.value],
        () => {
            if (instance.value) {
                if (visible.value) {
                    popper.value?.classList.remove("vue-use-popperjs-none");
                    instance.value?.update();
                } else {
                    popper.value?.classList.add("vue-use-popperjs-none");
                }
            }
        }
    );

    return {
        instance,
        visible,
    };
}
