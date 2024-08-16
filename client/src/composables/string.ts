import { type MaybeRefOrGetter, toValue } from "@vueuse/core";
import { computed, type Ref } from "vue";

import { ensureDefined } from "@/utils/assertions";

/**
 * Wraps a string ref to only allow values in a given set
 */
export function useInSet(stringRef: Ref<string>, set: MaybeRefOrGetter<string[]>): Ref<string> {
    const isInSet = (value: string) => {
        const allowedValues = new Set(toValue(set));
        return allowedValues.has(value);
    };

    const restrictedRef = computed<string>({
        get() {
            if (isInSet(stringRef.value)) {
                return stringRef.value;
            } else {
                return ensureDefined(toValue(set)[0], "set of allowed values needs to contain at least one value");
            }
        },
        set(value) {
            if (isInSet(value)) {
                stringRef.value = value;
            }
        },
    });

    return restrictedRef;
}
