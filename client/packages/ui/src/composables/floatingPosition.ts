import {
    autoUpdate,
    computePosition,
    type ComputePositionConfig,
    type MiddlewareData,
    type Placement,
} from "@floating-ui/dom";
import { type MaybeRefOrGetter, toValue } from "@vueuse/core";
import { onScopeDispose, ref, shallowRef, watch } from "vue";

/**
 * Keeps a floating element positioned against its reference element with floating-ui while `active`
 * is true, and stops tracking when it turns false or the owning scope is disposed.
 */
export function useFloatingPosition(
    reference: MaybeRefOrGetter<Element | null | undefined>,
    floating: MaybeRefOrGetter<HTMLElement | null | undefined>,
    active: MaybeRefOrGetter<boolean>,
    getConfig: () => Partial<ComputePositionConfig>,
) {
    const x = ref(0);
    const y = ref(0);
    const placement = ref<Placement>("bottom");
    const middlewareData = shallowRef<MiddlewareData>({});

    let cleanup: (() => void) | null = null;
    // Bumped by stop(), so a computePosition still in flight when tracking stops is discarded.
    let generation = 0;

    async function update() {
        const referenceElement = toValue(reference);
        const floatingElement = toValue(floating);
        if (!referenceElement || !floatingElement) {
            return;
        }

        const started = generation;
        const result = await computePosition(referenceElement, floatingElement, getConfig());
        if (started !== generation) {
            return;
        }
        x.value = result.x;
        y.value = result.y;
        placement.value = result.placement;
        middlewareData.value = result.middlewareData;
    }

    function stop() {
        generation++;
        cleanup?.();
        cleanup = null;
    }

    // Post flush, so a floating element revealed by v-show is laid out before it is measured.
    watch(
        [() => toValue(active), () => toValue(reference), () => toValue(floating)],
        ([isActive, referenceElement, floatingElement]) => {
            stop();
            if (isActive && referenceElement && floatingElement) {
                cleanup = autoUpdate(referenceElement, floatingElement, update);
            }
        },
        { flush: "post", immediate: true },
    );

    onScopeDispose(stop);

    return { x, y, placement, middlewareData, update };
}
