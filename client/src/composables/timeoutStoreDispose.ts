import type { Store } from "pinia";

const referenceCountByStore = new WeakMap<Store, number>();

/**
 * Reference counts a store, and provides a function to safely dispose it after a timeout.
 * @param store store to reference count and dispose
 * @param timeout how long to wait before reference counting and attempting a dispose.
 * @returns dispose function
 */
export function useTimeoutStoreDispose(store: Store, timeout = 1000) {
    const currentReferenceCount = referenceCountByStore.get(store) ?? 0;
    referenceCountByStore.set(store, currentReferenceCount + 1);

    const disposeIfReferenceFree = () => {
        const referenceCount = referenceCountByStore.get(store) ?? 0;

        if (referenceCount <= 0) {
            store.$dispose();
        }
    };

    const dispose = () => {
        const referenceCount = referenceCountByStore.get(store) ?? 1;
        referenceCountByStore.set(store, referenceCount - 1);
        setTimeout(disposeIfReferenceFree, timeout);
    };

    return dispose;
}
