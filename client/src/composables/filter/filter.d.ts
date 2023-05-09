import type { Ref } from "vue";
import type { MaybeComputedRef } from "@vueuse/core";

export declare function useFilterObjectArray<O extends object, K extends keyof O>(
    array: MaybeComputedRef<Array<O>>,
    filter: MaybeComputedRef<string>,
    objectFields: MaybeComputedRef<Array<K>>
): Ref<O>;
