import { useEventListener, useMutationObserver, usePreferredReducedMotion, useResizeObserver } from "@vueuse/core";
import { type Ref, ref } from "vue";

/** Sub-pixel scroll offsets still count as flush with the edge */
const EDGE_TOLERANCE = 1;

/**
 * Tracks which ends of a horizontally scrolling row hide content, so the row
 * can fade those edges instead of showing a scrollbar.
 */
export function useScrollEdges(element: Ref<HTMLElement | null>) {
    const fadeStart = ref(false);
    const fadeEnd = ref(false);
    const reducedMotion = usePreferredReducedMotion();

    function update() {
        const row = element.value;
        fadeStart.value = Boolean(row && row.scrollLeft > EDGE_TOLERANCE);
        fadeEnd.value = Boolean(row && row.scrollLeft + row.clientWidth < row.scrollWidth - EDGE_TOLERANCE);
    }

    /** Scrolls a child fully into the row, clear of the faded edges via `scroll-padding` */
    function revealChild(child: Element | null | undefined) {
        child?.scrollIntoView({
            behavior: reducedMotion.value === "reduce" ? "auto" : "smooth",
            block: "nearest",
            inline: "nearest",
        });
    }

    useEventListener(element, "scroll", update, { passive: true });
    // the row resizing and its chips changing both move the scroll extent
    useResizeObserver(element, update);
    useMutationObserver(element, update, { childList: true, characterData: true, subtree: true });

    return { fadeEnd, fadeStart, revealChild };
}
