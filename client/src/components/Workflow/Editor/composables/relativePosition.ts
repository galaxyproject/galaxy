import { type ZoomTransform } from "d3-zoom";
import { inject, onScopeDispose, type Ref, ref, watch } from "vue";

/**
 * Observe a section of the dom tree using a resize observer
 * @param child child node to start observation from
 * @param root root node to observe
 * @param observer resize observer to preform the observation
 */
function observeDomTree(child: Element, root: Element, observer: ResizeObserver) {
    let current: Element | null = child;

    while (current && current !== root) {
        observer.observe(current);
        current = current.parentElement;
    }

    observer.observe(root);
}

/**
 * Gets the relative position between a child element and a root element,
 * with transforms (e.g scale) applied
 * @param child element to get position of
 * @param root element to determine position relative to
 * @returns exact relative position in client space
 */
export function getRelativePosition(child: HTMLElement, root: HTMLElement) {
    const childBoundingBox = child.getBoundingClientRect();
    const rootBoundingBox = root.getBoundingClientRect();

    return {
        offsetLeft: childBoundingBox.left - rootBoundingBox.left,
        offsetTop: childBoundingBox.top - rootBoundingBox.top,
    };
}

export function useRelativePosition(child: Ref<HTMLElement | null>, root: Ref<HTMLElement | null>) {
    const position = ref({ offsetLeft: 0, offsetTop: 0 });
    const transform = inject("transform") as Ref<ZoomTransform>;

    // not supported by two mobile device browsers
    // eslint-disable-next-line compat/compat
    const observer = new ResizeObserver(() => {
        if (child.value && root.value) {
            const clientPosition = getRelativePosition(child.value, root.value);
            position.value = {
                offsetLeft: clientPosition.offsetLeft / transform.value.k,
                offsetTop: clientPosition.offsetTop / transform.value.k,
            };
        }
    });

    watch(
        [child, root],
        () => {
            observer.disconnect();

            if (child.value && root.value) {
                observeDomTree(child.value, root.value, observer);
            }
        },
        {
            immediate: true,
        }
    );

    onScopeDispose(() => {
        observer.disconnect();
    });

    return position;
}
