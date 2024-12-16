import { createPopper } from "@popperjs/core";
import { onMounted, onUnmounted, onUpdated, type Ref, ref, watch } from "vue";

export type Trigger = "hover" | "focus" | "click-to-open" | "click-to-toggle" | "manual";

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
                disabled: boolean | undefined;
                forceShow: boolean | undefined;
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

    const instance = ref<ReturnType<typeof createPopper>>();
    watch(
        () => [referenceRef.value, popperRef.value],
        () => {
            destroy();
            if (!referenceRef.value) {
                return;
            }
            if (!popperRef.value) {
                return;
            }
            concrete();
        }
    );
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
    const doToggle = () => (visible.value = !visible.value);
    const doOpen = () => (visible.value = true);
    const doClose = () => (visible.value = false);
    watch(
        () => [instance.value, options?.trigger, options?.forceShow],
        () => {
            if (instance.value) {
                if (options?.forceShow) {
                    visible.value = true;
                    doOff();
                    return;
                }

                doOn();
            }
        }
    );

    watch(
        () => options?.forceShow,
        () => {
            if (!options?.forceShow && options?.trigger !== "manual") {
                visible.value = false;
            }
        }
    );

    watch(
        () => options?.disabled,
        () => {
            if (options?.disabled) {
                doOff();
            } else {
                doOn();
            }
        }
    );

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
            case "click-to-open": {
                on(referenceRef.value!, "click", doOpen);
                on(document as any, "click", doCloseForDocument);
                break;
            }

            case "click-to-toggle": {
                on(referenceRef.value!, "click", doToggle);
                on(document as any, "click", doCloseForDocument);
                break;
            }

            case "hover": {
                on(referenceRef.value!, "mouseover", doMouseover);
                on(referenceRef.value!, "mouseout", doMouseout);
                on(referenceRef.value!, "mousedown", doMouseout);
                break;
            }

            case "focus": {
                on(referenceRef.value!, "focus", doOpen);
                on(referenceRef.value!, "blur", doClose);
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

        off(referenceRef.value!, "click", doToggle);

        off(referenceRef.value!, "mouseover", doMouseover);
        off(referenceRef.value!, "mouseout", doMouseout);
        off(referenceRef.value!, "mousedown", doMouseout);

        off(referenceRef.value!, "focus", doOpen);
        off(referenceRef.value!, "blur", doClose);
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
        () => [instance.value, visible.value],
        () => {
            if (instance.value) {
                if (visible.value || options?.forceShow) {
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
