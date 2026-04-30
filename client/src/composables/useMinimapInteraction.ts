import { useDraggable } from "@vueuse/core";
import { computed, type Ref, ref, unref, watch } from "vue";

import { useAnimationFrameThrottle } from "@/composables/throttle";
import { type AxisAlignedBoundingBox, Transform } from "@/utils/geometry";

export interface MinimapInteractionOptions {
    /** Canvas element for pointer interaction */
    canvasRef: Ref<HTMLCanvasElement | null>;
    /** Container element for resize dragging */
    containerRef: Ref<HTMLElement | null>;
    /** Reactive right/bottom edges of the parent element (for resize computation) */
    parentRight: Ref<number>;
    parentBottom: Ref<number>;
    /** Final content bounding box (consumer owns padding/squaring policy) */
    contentBounds: Ref<AxisAlignedBoundingBox>;
    /** Viewport bounding box in content coordinates */
    viewportBounds: Ref<AxisAlignedBoundingBox>;
    /** Called with content-coordinate delta when user drags the viewport */
    panBy: (delta: { x: number; y: number }) => void;
    /** Called with content-coordinate position when user clicks outside viewport */
    moveTo: (pos: { x: number; y: number }) => void;
    /** localStorage key for resize persistence */
    storageKey: string;
    /** Minimum minimap display size in pixels */
    minSize: number;
    /** Maximum minimap display size in pixels (also used as canvas internal resolution) */
    maxSize: number;
    /** Default minimap display size in pixels */
    defaultSize: number;
}

export function useMinimapInteraction(options: MinimapInteractionOptions) {
    const {
        canvasRef,
        containerRef,
        parentRight,
        parentBottom,
        contentBounds,
        viewportBounds,
        panBy,
        moveTo,
        storageKey,
        minSize,
        maxSize,
        defaultSize,
    } = options;

    // ── Transform: content coordinates → minimap canvas pixels ──

    let canvasTransform = new Transform();

    function recomputeTransform() {
        const canvas = unref(canvasRef);
        const bounds = unref(contentBounds);
        if (!canvas || bounds.width === 0 || bounds.height === 0) {
            canvasTransform = new Transform();
            return;
        }
        const scaleX = canvas.width / bounds.width;
        const scaleY = canvas.height / bounds.height;
        const s = Math.min(scaleX, scaleY);
        canvasTransform = new Transform().translate([-bounds.x * s, -bounds.y * s]).scale([s, s]);
    }

    watch(contentBounds, recomputeTransform, { deep: true });

    function getCanvasTransform(): Transform {
        return canvasTransform;
    }

    // ── Resize ──

    const minimapSize = ref(parseInt(localStorage.getItem(storageKey) || defaultSize.toString()));

    const { position: dragHandlePosition, isDragging: isHandleDragging } = useDraggable(containerRef, {
        preventDefault: true,
        exact: true,
    });

    const scaleFactor = computed(() => maxSize / minimapSize.value);

    watch(dragHandlePosition, () => {
        const newSize = Math.max(
            unref(parentRight) - dragHandlePosition.value.x,
            unref(parentBottom) - dragHandlePosition.value.y,
        );
        minimapSize.value = Math.min(Math.max(newSize, minSize), maxSize);
    });

    watch(isHandleDragging, () => {
        if (!isHandleDragging.value) {
            localStorage.setItem(storageKey, minimapSize.value.toString());
        }
    });

    // ── Pointer interaction: click-to-center / drag-to-pan ──

    const { throttle: dragThrottle } = useAnimationFrameThrottle();
    let dragViewport = false;

    function minimapToContent(offsetX: number, offsetY: number): [number, number] {
        return canvasTransform.inverse().scale([scaleFactor.value, scaleFactor.value]).apply([offsetX, offsetY]);
    }

    function minimapDeltaToContent(movementX: number, movementY: number): [number, number] {
        return canvasTransform
            .resetTranslation()
            .inverse()
            .scale([scaleFactor.value, scaleFactor.value])
            .apply([-movementX, -movementY]);
    }

    useDraggable(canvasRef, {
        onStart: (_position, event) => {
            const [x, y] = minimapToContent(event.offsetX, event.offsetY);
            if (unref(viewportBounds).isPointInBounds({ x, y })) {
                dragViewport = true;
            }
        },
        onMove: (_position, event) => {
            dragThrottle(() => {
                if (!dragViewport) {
                    return;
                }
                const [x, y] = minimapDeltaToContent(event.movementX, event.movementY);
                panBy({ x, y });
            });
        },
        onEnd: (_position, event) => {
            if (!dragViewport) {
                const [x, y] = minimapToContent(event.offsetX, event.offsetY);
                moveTo({ x, y });
            }
            dragViewport = false;
        },
    });

    return {
        getCanvasTransform,
        recomputeTransform,
        minimapSize,
    };
}
