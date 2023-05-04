import { onScopeDispose, ref, watch, type Ref } from "vue";
import type { MaybeComputedRef } from "@vueuse/core";
import { resolveUnref } from "@vueuse/core";
import type { Message, ResultMessage } from "./filter.worker";

/**
 * Reactively filter an array of objects, by comparing `filter` to all `fields`.
 * All parameters can optionally be refs.
 * @param array array of objects to filter
 * @param filter string to filter by
 * @param objectFields string array of fields to filter by on each object
 */
export function useFilterObjectArray<O extends object, K extends keyof O>(
    array: MaybeComputedRef<Array<O>>,
    filter: MaybeComputedRef<string>,
    objectFields: MaybeComputedRef<Array<K>>
) {
    const worker = new Worker(new URL("./filter.worker.ts", import.meta.url));

    const filtered: Ref<O[]> = ref([]);
    filtered.value = resolveUnref(array);

    const post = (message: Message<O, K>) => {
        worker.postMessage(message);
    };

    watch(
        () => resolveUnref(array),
        (arr) => {
            post({ type: "setArray", array: arr });
        },
        {
            immediate: true,
        }
    );

    watch(
        () => resolveUnref(filter),
        (f) => {
            post({ type: "setFilter", filter: f });
        },
        {
            immediate: true,
        }
    );

    watch(
        () => resolveUnref(objectFields),
        (fields) => {
            post({ type: "setFields", fields });
        },
        {
            immediate: true,
        }
    );

    worker.onmessage = (e: MessageEvent<ResultMessage<O>>) => {
        const message = e.data;

        if (message.type === "result") {
            filtered.value = message.filtered;
        }
    };

    onScopeDispose(() => {
        worker.terminate();
    });

    return filtered;
}
