import type { Ref } from "vue";
import type { MaybeComputedRef } from "@vueuse/core";

/**
 * Reactively filter an array of objects, by comparing `filter` to all `fields`.
 * All parameters can optionally be refs.
 * @param array array of objects to filter
 * @param filter string to filter by
 * @param objectFields string array of fields to filter by on each object
 */
export declare function useFilterObjectArray<O extends object, K extends keyof O>(
    array: MaybeComputedRef<Array<O>>,
    filter: MaybeComputedRef<string>,
    objectFields: MaybeComputedRef<Array<K>>
): Ref<O[]>;
