import { type MaybeRefOrGetter } from "@vueuse/core";
import { type Ref } from "vue";

/**
 * Reactively filter an array of objects, by comparing `filter` to all `fields`.
 * All parameters can optionally be refs.
 * @param array array of objects to filter
 * @param filter string to filter by
 * @param objectFields string array of fields to filter by on each object. To reach nested fields, use an array of strings (e.g. `["nested", "field"]`)
 */
export declare function useFilterObjectArray<O extends object, K extends keyof O>(
    array: MaybeRefOrGetter<Array<O>>,
    filter: MaybeRefOrGetter<string>,
    objectFields: MaybeRefOrGetter<Array<K | string[]>>
): Ref<O[]>;
