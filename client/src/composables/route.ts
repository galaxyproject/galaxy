import { MaybeComputedRef, resolveUnref } from "@vueuse/core";
import { computed } from "vue";
import { useRoute } from "vue-router/composables";

/** use a route query parameter as a boolean computed */
export function useRouteQueryBool(
    parameter: MaybeComputedRef<string>,
    defaultValue: MaybeComputedRef<boolean> = false
) {
    const route = useRoute();
    return computed(() => {
        const p = resolveUnref(parameter);
        return p in route.query ? route.query[p] === "true" : resolveUnref(defaultValue);
    });
}

export function useRouteQueryNumber(parameter: MaybeComputedRef<string>, defaultValue: MaybeComputedRef<number> = 1) {
    const route = useRoute();
    return computed(() => {
        const p = resolveUnref(parameter);
        if (p in route.query) {
            const v = route.query[p];
            return typeof v === "string" ? parseFloat(v) : resolveUnref(defaultValue);
        } else {
            return resolveUnref(defaultValue);
        }
    });
}
