import { reactive, unref, watchEffect, inject } from "vue";
import { useElementBounding } from "@vueuse/core";

/**
 * Return the element position relative to the child of the element that determines rootOffset
 * @param {MaybeComputedElementRef} target - HTML element reference for which to calculate coordinates
 * @param {Object} rootOffset - Bounding rectangle of element that determines the canvas coordinates
 * @param {Object} parentOffset - Bounding rectangle of direct parent.
 */
export function useCoordinatePosition(target, rootOffset, parentOffset = null, stepPosition = null) {
    const position = reactive(useElementBounding(target, { windowResize: false }));
    const offset = unref(rootOffset);
    const transform = inject("transform");
    const parent = unref(parentOffset);
    const step = unref(stepPosition);

    watchEffect(() => {
        /*
         * Touch parentOffset to establish dependency, so that changes in parentOffset
         * force an update of child coordinates, think addition/removal of extra outputs,
         * adding a long label, etc.
         */
        parent?.height;
        step?.left;
        step?.top;
        position.update();
        // Apply scale and offset so that position is in an unscaled coordinate system
        applyTransform(position, offset, transform);
    });
    return position;
}

export function applyTransform(position, offset, transform) {
    position.top = (position.top - offset.top - transform.y) / transform.k;
    position.left = (position.left - offset.left - transform.x) / transform.k;
    position.width /= transform.k;
    position.height /= transform.k;
    position.bottom = position.top + position.height;
    position.right = position.left + position.width;
}
