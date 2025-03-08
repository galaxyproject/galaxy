import { type MaybeRefOrGetter, toValue } from "@vueuse/core";
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

/** use a route query parameter as a boolean computed */
export function useRouteQueryBool(
    parameter: MaybeRefOrGetter<string>,
    defaultValue: MaybeRefOrGetter<boolean> = false
) {
    const route = useRoute();
    return computed(() => {
        const p = toValue(parameter);
        return p in route.query ? route.query[p] === "true" : toValue(defaultValue);
    });
}

export function useRouteQueryNumber(parameter: MaybeRefOrGetter<string>, defaultValue: MaybeRefOrGetter<number> = 1) {
    const route = useRoute();
    return computed(() => {
        const p = toValue(parameter);
        if (p in route.query) {
            const v = route.query[p];
            return typeof v === "string" ? parseFloat(v) : toValue(defaultValue);
        } else {
            return toValue(defaultValue);
        }
    });
}

export function useToolRouting() {
    const router = useRouter();

    function routeToTool(toolId: string) {
        router.push(`/?tool_id=${encodeURIComponent(toolId)}&version=latest`);
    }
    return { routeToTool };
}
