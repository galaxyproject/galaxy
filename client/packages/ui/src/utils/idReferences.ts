/** Helpers for attributes that hold a space-separated list of element ids, such as aria-describedby. */

function readIds(el: Element, attribute: string): string[] {
    return (el.getAttribute(attribute) ?? "").split(/\s+/).filter(Boolean);
}

/** Appends an id to an id-list attribute, keeping the ids that others put there. */
export function addIdReference(el: Element, attribute: string, id: string) {
    const ids = readIds(el, attribute);
    if (!ids.includes(id)) {
        el.setAttribute(attribute, [...ids, id].join(" "));
    }
}

/** Removes one id from an id-list attribute, and the attribute itself once the list is empty. */
export function removeIdReference(el: Element, attribute: string, id: string) {
    const ids = readIds(el, attribute).filter((existing) => existing !== id);
    if (ids.length) {
        el.setAttribute(attribute, ids.join(" "));
    } else {
        el.removeAttribute(attribute);
    }
}
