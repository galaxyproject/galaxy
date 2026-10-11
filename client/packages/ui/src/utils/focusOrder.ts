// Positive tabindex values are rare enough here that document order stands in for the full sequential focus order.
const FOCUSABLE_SELECTOR = [
    "a[href]",
    "area[href]",
    "button:not([disabled])",
    'input:not([disabled]):not([type="hidden"])',
    "select:not([disabled])",
    "textarea:not([disabled])",
    "summary",
    "iframe",
    "audio[controls]",
    "video[controls]",
    '[contenteditable]:not([contenteditable="false"])',
    "[tabindex]",
].join(", ");

function isRendered(element: HTMLElement) {
    // checkVisibility also covers visibility: hidden; getClientRects is empty for anything under display: none.
    if (typeof element.checkVisibility === "function") {
        return element.checkVisibility({ visibilityProperty: true });
    }
    return element.getClientRects().length > 0;
}

// `[tabindex]` also matches disabled controls, which take no focus; the costly isRendered goes last.
function isTabbable(element: HTMLElement) {
    const tabindex = element.getAttribute("tabindex");
    return (
        !(tabindex !== null && Number(tabindex) < 0) &&
        !element.matches(":disabled") &&
        !element.closest("[inert]") &&
        isRendered(element)
    );
}

/** Elements inside root that Tab stops on, in document order */
export function tabbableElements(root: ParentNode): HTMLElement[] {
    return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(isTabbable);
}

/** The first element inside root that Tab stops on after anchor and outside it, skipping any that skip() rejects */
export function nextTabbableAfter(
    anchor: Element,
    root: ParentNode,
    skip: (element: HTMLElement) => boolean = () => false,
): HTMLElement | undefined {
    // Position and skip() first, so only candidates after the anchor pay for the visibility check.
    return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).find(
        (element) =>
            !anchor.contains(element) &&
            Boolean(anchor.compareDocumentPosition(element) & Node.DOCUMENT_POSITION_FOLLOWING) &&
            !skip(element) &&
            isTabbable(element),
    );
}
