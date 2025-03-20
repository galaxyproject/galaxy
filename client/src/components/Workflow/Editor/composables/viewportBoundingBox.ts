import { type UseElementBoundingReturn } from "@vueuse/core";
import { type Ref, ref, unref, watch } from "vue";

import { useAnimationFrameThrottle } from "@/composables/throttle";

import { AxisAlignedBoundingBox } from "../modules/geometry";

/**
 * Constructs a bounding box following the editors pan and zoom in
 * animation frame intervals.
 *
 * @param bounds vueuse bounding box
 * @param scale scale to apply to bounding box
 * @param pan pan to apply to bounding box
 * @returns Axis Aligned Bounding Box following the viewport
 */
export function useViewportBoundingBox(
    bounds: UseElementBoundingReturn,
    scale: Ref<number>,
    pan: Ref<{ x: number; y: number }>
) {
    const { throttle } = useAnimationFrameThrottle(100);

    const viewportBoundingBox = ref(new AxisAlignedBoundingBox());
    watch(
        () => ({
            x: unref(pan).x,
            y: unref(pan).y,
            scale: unref(scale),
            width: unref(bounds.width),
            height: unref(bounds.height),
        }),
        ({ x, y, scale, width, height }) => {
            throttle(() => {
                const bounds = viewportBoundingBox.value;

                bounds.x = -x / scale;
                bounds.y = -y / scale;
                bounds.width = width / scale;
                bounds.height = height / scale;

                viewportBoundingBox.value = bounds;
            });
        }
    );

    return { viewportBoundingBox };
}
