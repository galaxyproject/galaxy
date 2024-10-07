import { toValue } from "@vueuse/core";
import { onScopeDispose, ref, watchEffect } from "vue";

let worker;
let idCounter = 0;
let workerReferenceCount = 0;

export function useFilterObjectArray(array, filter, objectFields) {
    if (!worker) {
        worker = new Worker(new URL("./filter.worker.js", import.meta.url));
    }

    workerReferenceCount += 1;
    const id = idCounter++;

    const post = (message) => {
        worker.postMessage({ id, ...message });
    };

    const filtered = ref([]);
    filtered.value = toValue(array);

    const onMessage = (e) => {
        const message = e.data;

        // exit if message is not meant for this composable instance
        if (message.id !== id) {
            return;
        }

        if (message.type === "result") {
            filtered.value = message.filtered;
        } else {
            post({ type: "clear" });
            worker.removeEventListener("message", onMessage);
        }
    };

    worker.addEventListener("message", onMessage);

    watchEffect(() => {
        post({ type: "setArray", array: toValue(array) });
    });

    watchEffect(() => {
        post({ type: "setFilter", filter: toValue(filter) });
    });

    watchEffect(() => {
        post({ type: "setFields", fields: toValue(objectFields) });
    });

    onScopeDispose(() => {
        workerReferenceCount -= 1;

        if (workerReferenceCount <= 0) {
            worker.terminate();
            worker = null;
        }
    });

    return filtered;
}
