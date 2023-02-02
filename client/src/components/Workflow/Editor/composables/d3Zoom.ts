import { zoom, zoomIdentity, type D3ZoomEvent } from "d3-zoom";
import { ref, watch } from "vue";
import { select } from "d3-selection";
import type { Ref } from "vue";
import type { XYPosition } from "@/stores/workflowEditorStateStore";
import type { UseScrollReturn } from "@vueuse/core";

// if element is draggable it may implement its own drag handler,
// but d3zoom would call preventDefault
const filter = (event: any) => {
    const preventZoom = event.target.classList.contains("prevent-zoom");
    return !preventZoom;
};

export function useD3Zoom(
    k: number,
    minZoom: number,
    maxZoom: number,
    targetRef: Ref<HTMLElement | null>,
    scroll: UseScrollReturn,
    initialPan: XYPosition = { x: 0, y: 0 }
) {
    const transform = ref({ x: initialPan.x, y: initialPan.y, k: k });
    const d3Zoom = zoom<HTMLElement, unknown>().filter(filter).scaleExtent([minZoom, maxZoom]);

    watch(targetRef, () => {
        if (targetRef.value) {
            const d3Selection = select(targetRef.value).call(d3Zoom);
            const updatedTransform = zoomIdentity
                .translate(transform.value.x, transform.value.y)
                .scale(transform.value.k);
            d3Zoom.transform(d3Selection, updatedTransform);
        }

        d3Zoom.on("zoom", (event: D3ZoomEvent<HTMLElement, unknown>) => {
            transform.value = event.transform;
        });

        d3Zoom.on("start", (event: D3ZoomEvent<HTMLElement, unknown>) => {
            transform.value = event.transform;
        });

        d3Zoom.on("end", (event: D3ZoomEvent<HTMLElement, unknown>) => {
            transform.value = event.transform;
        });
    });

    function setZoom(k: number) {
        if (targetRef.value) {
            const d3Selection = select(targetRef.value).call(d3Zoom);
            d3Zoom.scaleTo(d3Selection, k);
        }
    }

    function panBy(panBy: XYPosition) {
        if (targetRef.value) {
            const d3Selection = select(targetRef.value).call(d3Zoom);
            d3Zoom.translateBy(d3Selection, panBy.x, panBy.y);
        }
    }

    function moveTo(coordinate: XYPosition) {
        if (targetRef.value) {
            const d3Selection = select(targetRef.value).call(d3Zoom);
            d3Zoom.translateTo(d3Selection, coordinate.x, coordinate.y);
        }
    }

    return { transform, setZoom, panBy, moveTo };
}
