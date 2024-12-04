import { useRoute } from "vue-router/composables";

export function getQueryValue(key: string): string | undefined {
    const route = useRoute();

    return (Array.isArray(route.query[key]) ? route.query[key]?.[0] : route.query[key])?.toString();
}
