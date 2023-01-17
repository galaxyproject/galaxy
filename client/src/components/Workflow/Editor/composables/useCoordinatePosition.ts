import { reactive, watchEffect, inject, type UnwrapRef, type Ref } from "vue";
import { useElementBounding, type MaybeComputedElementRef, type UseElementBoundingReturn } from "@vueuse/core";
import type { Step } from "@/stores/workflowStepStore";
import type { ZoomTransform } from "d3-zoom";

export type ElementBounding = UnwrapRef<UseElementBoundingReturn>;

/**
 * Return the element position relative to the child of the element that determines rootOffset
 * @param {MaybeComputedElementRef} target - HTML element reference for which to calculate coordinates
 * @param {Object} rootOffset - Bounding rectangle of element that determines the canvas coordinates
 * @param {Object} parentOffset - Bounding rectangle of direct parent.
 */
export function useCoordinatePosition(
    target: MaybeComputedElementRef,
    rootOffset: Ref<ElementBounding>,
    stepPosition: Ref<NonNullable<Step["position"]>>
) {
    const elementBounding = useElementBounding(target, { windowResize: false });
    const transform = inject("transform") as Ref<ZoomTransform>;
    let position: ElementBounding = reactive(elementBounding);

    watchEffect(() => {
        /*
         * Touch parentOffset to establish dependency, so that changes in parentOffset
         * force an update of child coordinates, think addition/removal of extra outputs,
         * adding a long label, etc.
         *
         * Maybe this can be simplified ? I think the way I'm using reactive I'm dismissing updated values from useCoordinatePosition run
         * before I hit watchEffect
         */
        position = reactive(elementBounding);
        stepPosition.value.left;
        stepPosition.value.top;
        const offset = reactive(rootOffset.value);
        position.update();
        // Apply scale and offset so that position is in an unscaled coordinate system
        applyTransform(position, offset, transform.value);
    });
    return position;
}

export function applyTransform(position: ElementBounding, offset: ElementBounding, transform: ZoomTransform) {
    position.top = (position.top - offset.top - transform.y) / transform.k;
    position.left = (position.left - offset.left - transform.x) / transform.k;
    position.width /= transform.k;
    position.height /= transform.k;
    position.bottom = position.top + position.height;
    position.right = position.left + position.width;
    return position;
}
