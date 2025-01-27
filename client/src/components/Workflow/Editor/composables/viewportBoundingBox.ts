import { type UseElementBoundingReturn } from "@vueuse/core";
import { type Ref, ref, unref, watch } from "vue";

import { useAnimationFrameThrottle } from "@/composables/throttle";

import { AxisAlignedBoundingBox } from "../modules/geometry";

/**
 * Constructs a bounding box following the editors pan and zoom in
 * animation frame intervals.
 *
 * @param bounds vueuse bounding box
 * @param zoom zoom to apply to bounding box
 * @param pan pan to apply to bounding box
 * @returns Axis Aligned Bounding Box following the viewport
 */
export function useViewportBoundingBox(
    bounds: UseElementBoundingReturn,
    zoom: Ref<number>,
    pan: Ref<{ x: number; y: number }>
) {
    const { throttle } = useAnimationFrameThrottle(100);

    const viewportBaseBoundingBox = ref(new AxisAlignedBoundingBox());
    const viewportBoundingBox = ref(new AxisAlignedBoundingBox());

    const updateViewportBaseBoundingBox = () => {
        const width = unref(bounds.width);
        const height = unref(bounds.height);

        viewportBaseBoundingBox.value.x = 0;
        viewportBaseBoundingBox.value.y = 0;

        viewportBaseBoundingBox.value.width = width;
        viewportBaseBoundingBox.value.height = height;

        return viewportBaseBoundingBox.value;
    };

    const updateViewportBoundingBox = () => {
        const { width, height } = updateViewportBaseBoundingBox();

        const x = unref(pan).x;
        const y = unref(pan).y;
        const scaleValue = 1.0 / unref(zoom);

        viewportBoundingBox.value.move([-x * scaleValue, -y * scaleValue]);
        viewportBoundingBox.value.width = width * scaleValue;
        viewportBoundingBox.value.height = height * scaleValue;

        return viewportBoundingBox.value;
    };

    watch(
        () => ({
            x: unref(pan).x,
            y: unref(pan).y,
            scale: unref(zoom),
            width: unref(bounds.width),
            height: unref(bounds.height),
        }),
        () => {
            throttle(() => {
                updateViewportBoundingBox();
            });
        }
    );

    return { viewportBoundingBox, updateViewportBoundingBox, viewportBaseBoundingBox, updateViewportBaseBoundingBox };
}
