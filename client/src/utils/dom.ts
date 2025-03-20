/**
 * composed array of all Event Targets between the original and current target
 *
 * @param e Event to return partial composed path of
 */
export function composedPartialPath(e: Event): EventTarget[] {
    const current = e.currentTarget;
    const composed = e.composedPath();

    const currentIndex = composed.findIndex((target) => target === current);

    if (currentIndex === -1) {
        throw new Error("current target is not part of composed path");
    }

    const partial = composed.slice(0, currentIndex);

    return partial;
}

/**
 * checks if an element has a valid mouse interaction
 */
export function isClickable(element: Element): boolean {
    const clickable =
        element instanceof HTMLButtonElement ||
        element instanceof HTMLInputElement ||
        element instanceof HTMLAnchorElement ||
        element instanceof HTMLSelectElement ||
        element instanceof HTMLLabelElement;

    return clickable;
}
