import { type UseScrollReturn } from "@vueuse/core";
import { select } from "d3-selection";
import { type D3ZoomEvent, zoom, zoomIdentity } from "d3-zoom";
import { type Ref, ref, watch } from "vue";

import { type XYPosition } from "@/stores/workflowEditorStateStore";

// if element is draggable it may implement its own drag handler,
// but d3zoom would call preventDefault
const filter = (event: D3ZoomEvent<HTMLElement, unknown>["sourceEvent"]) => {
    const target = event.target as HTMLElement;

    if (target.classList.contains("prevent-zoom")) {
        return false;
    }

    if (event.type === "dblclick") {
        const style = getComputedStyle(target);

        if (style.getPropertyValue("--dblclick") === "prevent") {
            return false;
        }
    }

    return true;
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
