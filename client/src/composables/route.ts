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
