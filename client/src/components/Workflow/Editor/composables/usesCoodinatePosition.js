import { reactive, unref, watchEffect } from "vue";
import { useElementBounding } from "@vueuse/core";

/**
 * Return the element position relative to the child of the element that determines rootOffset
 * @param {MaybeComputedElementRef} target - HTML element reference for which to calculate coordinates
 * @param {Object} rootOffset - Bounding rectangle of element that determines the canvas coordinates
 */
export function useCoordinatePosition(target, rootOffset, parentOffset = null) {
    const position = reactive(useElementBounding(target, { windowResize: false }));
    const offset = unref(rootOffset);
    parent = unref(parentOffset);

    watchEffect(() => {
        parentOffset?.height; // just touch parentOffset to establish dependency
        position.update();
        position.top -= offset.top;
        position.left -= offset.left;
    });
    return position;
}
