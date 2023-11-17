import { onScopeDispose, ref, watchEffect } from "vue";

// glue code together with the .worker.js file, to run `main` in a thread

export function useSelectMany({
    optionsArray,
    filter,
    unselected,
    selected,
    unselectedDisplayCount,
    selectedDisplayCount,
    asRegex,
    caseSensitive,
}) {
    const worker = new Worker(new URL("./selectMany.worker.js", import.meta.url));

    const unselectedOptionsFiltered = ref([]);
    const selectedOptionsFiltered = ref([]);
    const running = ref(false);

    const post = (message) => {
        worker.postMessage(message);
        running.value = true;
    };

    onScopeDispose(() => {
        worker.terminate();
    });

    watchEffect(() => {
        post({ type: "setArray", array: optionsArray.value });
    });

    watchEffect(() => {
        post({ type: "setFilter", filter: filter.value });
    });

    watchEffect(() => {
        post({ type: "setUnselected", unselected: unselected.value });
    });

    watchEffect(() => {
        post({ type: "setSelected", selected: selected.value });
    });

    watchEffect(() => {
        post({
            type: "setSettings",
            unselectedDisplayCount: unselectedDisplayCount.value,
            selectedDisplayCount: selectedDisplayCount.value,
            asRegex: asRegex.value,
            caseSensitive: caseSensitive.value,
        });
    });

    worker.onmessage = (e) => {
        const message = e.data;

        if (message.type === "result") {
            unselectedOptionsFiltered.value = message.unselectedOptionsFiltered;
            selectedOptionsFiltered.value = message.selectedOptionsFiltered;
            running.value = false;
        }
    };

    return {
        unselectedOptionsFiltered,
        selectedOptionsFiltered,
        running,
    };
}
