/** Immediately report observed elements as visible for visibility-driven tests. */
export class VisibleIntersectionObserver implements IntersectionObserver {
    readonly root = null;
    readonly rootMargin = "0px";
    readonly thresholds = [0];

    constructor(private callback: IntersectionObserverCallback) {}

    observe(target: Element) {
        const bounds = target.getBoundingClientRect();
        this.callback(
            [
                {
                    isIntersecting: true,
                    intersectionRatio: 1,
                    time: 1,
                    target,
                    boundingClientRect: bounds,
                    intersectionRect: bounds,
                    rootBounds: null,
                },
            ],
            this,
        );
    }

    unobserve() {}
    disconnect() {}
    takeRecords(): IntersectionObserverEntry[] {
        return [];
    }
}
