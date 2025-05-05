import { onScopeDispose, ref, watchEffect } from "vue";

// glue code together with the .worker.js file, to run `main` in a thread

let worker;
let idCounter = 0;
let workerReferenceCount = 0;

export function useSelectMany({
    optionsArray,
    filter,
    selected,
    unselectedDisplayCount,
    selectedDisplayCount,
    caseSensitive,
    maintainSelectionOrder,
}) {
    // only start a single worker
    if (!worker) {
        worker = new Worker(new URL("./selectMany.worker.js", import.meta.url));
    }

    workerReferenceCount += 1;

    const id = idCounter++;

    const unselectedOptionsFiltered = ref([]);
    const selectedOptionsFiltered = ref([]);
    const moreSelected = ref(false);
    const moreUnselected = ref(false);
    const running = ref(false);

    const post = (message) => {
        worker.postMessage({ id, ...message });
        running.value = true;
    };

    onScopeDispose(() => {
        workerReferenceCount -= 1;

        if (workerReferenceCount === 0) {
            worker.terminate();
            worker = null;
        } else {
            post({ type: "clear" });
            worker.removeEventListener("message", onMessage);
        }
    });

    watchEffect(() => {
        post({ type: "setArray", array: optionsArray.value });
    });

    watchEffect(() => {
        post({ type: "setFilter", filter: filter.value });
    });

    watchEffect(() => {
        post({ type: "setSelected", selected: selected.value });
    });

    watchEffect(() => {
        post({
            type: "setSettings",
            unselectedDisplayCount: unselectedDisplayCount.value,
            selectedDisplayCount: selectedDisplayCount.value,
            caseSensitive: caseSensitive.value,
            maintainSelectionOrder: maintainSelectionOrder.value,
        });
    });

    const onMessage = (e) => {
        const message = e.data;

        if (message.id !== id) {
            return;
        }

        if (message.type === "result") {
            unselectedOptionsFiltered.value = message.unselectedOptionsFiltered;
            selectedOptionsFiltered.value = message.selectedOptionsFiltered;
            moreSelected.value = message.moreSelected;
            moreUnselected.value = message.moreUnselected;
            running.value = false;
        }
    };

    worker.addEventListener("message", onMessage);

    return {
        unselectedOptionsFiltered,
        selectedOptionsFiltered,
        moreSelected,
        moreUnselected,
        running,
    };
}
