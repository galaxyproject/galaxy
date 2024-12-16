import { createPopper } from "@popperjs/core";
import { onMounted, onUnmounted, onUpdated, type Ref, ref, watch } from "vue";

export type Trigger = "click" | "hover" | "manual";

export type EventOptions = {
    onShow: () => void;
    onHide: () => void;
};

function on(element: Element, event: string, handler: EventListenerOrEventListenerObject) {
    if (element && event && handler) {
        element.addEventListener(event, handler, false);
    }
}
function off(element: Element, event: string, handler: EventListenerOrEventListenerObject) {
    if (element && event) {
        element.removeEventListener(event, handler, false);
    }
}

const defaultTrigger: Trigger = "hover";

export function usePopperjs(
    reference: Ref<Parameters<typeof createPopper>["0"]>,
    popper: Ref<Parameters<typeof createPopper>["1"]>,
    options?: Partial<
        Parameters<typeof createPopper>["2"] &
            EventOptions & {
                trigger: Trigger | undefined;
                delayOnMouseover: number | undefined;
                delayOnMouseout: number | undefined;
            }
    >
) {
    const isMounted = ref(false);
    onMounted(() => {
        isMounted.value = true;
    });
    onUnmounted(() => {
        isMounted.value = false;
        destroy();
    });

    const updatedFlag = ref(true);
    onUpdated(() => {
        updatedFlag.value = !updatedFlag.value;
    });

    const referenceRef = ref<Element>();
    const popperRef = ref<HTMLElement>();
    const instance = ref<ReturnType<typeof createPopper>>();

    const concrete = () => {
        instance.value = createPopper(referenceRef.value!, popperRef.value!, {
            placement: options?.placement ?? "bottom",
            modifiers: options?.modifiers ?? [],
            strategy: options?.strategy ?? "absolute",
            onFirstUpdate: options?.onFirstUpdate ?? undefined,
        });
    };

    const destroy = () => {
        instance.value?.destroy();
        instance.value = undefined;
    };

    const visible = ref(false);
    const doOpen = () => (visible.value = true);
    const doClose = () => (visible.value = false);

    const timer = ref<any>();

    const doMouseover = () => {
        if (options?.delayOnMouseover === 0) {
            doOpen();
        } else {
            clearTimeout(timer.value);
            timer.value = setTimeout(() => {
                doOpen();
            }, options?.delayOnMouseover ?? 100);
        }
    };

    const doMouseout = () => {
        if (options?.delayOnMouseout === 0) {
            doClose();
        } else {
            clearTimeout(timer.value);
            timer.value = setTimeout(() => {
                doClose();
            }, options?.delayOnMouseout ?? 100);
        }
    };

    const doOn = () => {
        doOff();

        switch (options?.trigger ?? defaultTrigger) {
            case "click": {
                on(referenceRef.value!, "click", doOpen);
                on(document as any, "click", doCloseForDocument);
                break;
            }

            case "hover": {
                on(referenceRef.value!, "mouseover", doMouseover);
                on(referenceRef.value!, "mouseout", doMouseout);
                on(referenceRef.value!, "mousedown", doMouseout);
                break;
            }

            case "manual": {
                break;
            }

            default: {
                throw TypeError();
            }
        }
    };

    const doOff = () => {
        off(referenceRef.value!, "click", doOpen);
        off(document as any, "click", doCloseForDocument);

        off(referenceRef.value!, "mouseover", doMouseover);
        off(referenceRef.value!, "mouseout", doMouseout);
        off(referenceRef.value!, "mousedown", doMouseout);
    };

    const doCloseForDocument = (e: Event) => {
        if (referenceRef.value?.contains(e.target as Element)) {
            return;
        }
        if (popperRef.value?.contains(e.target as Element)) {
            return;
        }
        doClose();
    };

    watch(
        () => [isMounted.value, updatedFlag.value],
        () => {
            if (isMounted.value) {
                if ((reference.value as any)?.$el) {
                    referenceRef.value = (reference.value as any).$el;
                } else {
                    referenceRef.value = reference.value as Element;
                }

                if ((popper.value as any)?.$el) {
                    popperRef.value = (popper.value as any).$el;
                } else {
                    popperRef.value = popper.value;
                }
            }
        }
    );

    watch(
        () => [referenceRef.value, popperRef.value],
        () => {
            destroy();
            if (referenceRef.value && popperRef.value) {
                concrete();
            }
        }
    );

    watch(
        () => [instance.value, options?.trigger],
        () => {
            if (instance.value) {
                doOn();
            }
        }
    );

    watch(
        () => [instance.value, visible.value],
        () => {
            if (instance.value) {
                if (visible.value) {
                    popperRef.value?.classList.remove("vue-use-popperjs-none");
                    options?.onShow?.();
                    instance.value?.update();
                } else {
                    popperRef.value?.classList.add("vue-use-popperjs-none");
                    options?.onHide?.();
                }
            }
        }
    );

    return {
        instance,
        visible,
    };
}
