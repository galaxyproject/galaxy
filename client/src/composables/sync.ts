import { type MaybeRefOrGetter, toValue } from "@vueuse/core";
import { type Ref, watch } from "vue";

/** One-way sync source ref, computed or getter function to target ref */
export function useSync<T>(source: MaybeRefOrGetter<T>, target: Ref<T>) {
    watch(
        () => toValue(source),
        (value) => (target.value = value),
        { immediate: true }
    );
}
